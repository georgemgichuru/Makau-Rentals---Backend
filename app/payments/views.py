import base64
import datetime
import json
import requests
import csv
import time
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from datetime import timedelta
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from accounts.models import CustomUser, Subscription, Property, Unit, UnitType
# Removed require_subscription import as it's no longer used
from accounts.serializers import UnitTypeSerializer
from .models import Payment, SubscriptionPayment
from .generate_token import generate_access_token, initiate_b2c_payment
from rest_framework import generics, permissions
from .serializers import PaymentSerializer, SubscriptionPaymentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from accounts.permissions import IsLandlord, HasActiveSubscription
# ------------------------------
# STK PUSH INITIATION (Tenant Rent Payment) - UPDATED
# ------------------------------
@csrf_exempt
def stk_push(request, unit_id):
    """
    Initiates an M-Pesa STK Push for a tenant's rent payment.
    """
    logger = logging.getLogger(__name__)

    # Check authentication first
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.user.user_type != 'tenant':
        return JsonResponse({"error": "Only tenants can make rent payments"}, status=403)

    try:
        if request.method != 'POST':
            return JsonResponse({"error": "POST method required."}, status=405)

        # Parse JSON body
        try:
            body = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        # Get amount from JSON data
        amount_str = body.get('amount')
        if not amount_str:
            return JsonResponse({"error": "Amount is required."}, status=400)

        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            return JsonResponse({"error": "Invalid amount format."}, status=400)
        
        # Rate limiting: Check if user has made too many requests
        rate_limit_key = f"stk_push_rate_limit:{request.user.id}"
        recent_requests = cache.get(rate_limit_key, 0)
        if recent_requests >= 5:  # Max 5 requests per minute
            return JsonResponse({"error": "Too many requests. Please try again later."}, status=429)
        
        # Update rate limit counter
        cache.set(rate_limit_key, recent_requests + 1, timeout=60)
        
        # REQUIRE tenant to be assigned to unit for rent payments
        try:
            unit = Unit.objects.get(id=unit_id, tenant=request.user)
        except Unit.DoesNotExist:
            return JsonResponse({"error": "Unit not found or you are not assigned to this unit. Please pay deposit first."}, status=404)
        
        # Validate amount
        if amount <= 0:
            return JsonResponse({"error": "Amount must be positive."}, status=400)
        
        # Allow any amount that's at least the rent (for testing)
        if amount < unit.rent:
            return JsonResponse({"error": f"Amount must be at least the monthly rent ({unit.rent})."}, status=400)
        
        # More generous maximum for testing
        max_amount = unit.rent * 24  # Allow up to 2 years rent for testing
        if amount > max_amount:
            return JsonResponse({"error": f"Amount cannot exceed two years' rent ({max_amount})."}, status=400)
        
        # Check for duplicate pending payment
        duplicate_key = f"pending_payment:{request.user.id}:{unit_id}"
        if cache.get(duplicate_key):
            return JsonResponse({"error": "A payment request is already pending for this unit."}, status=400)
        
        # Create a pending payment record
        payment = Payment.objects.create(
            tenant=request.user,
            unit=unit,
            amount=amount,
            status="Pending"
        )
        
        # Mark payment as pending in Redis (5-minute expiry)
        cache.set(duplicate_key, payment.id, timeout=300)
        
        # Check if tenant has paid deposit for this unit (REQUIRED)
        deposit_paid = Payment.objects.filter(
            tenant=request.user,
            unit=unit,
            payment_type='deposit',
            status='Success',
            amount__gte=unit.deposit
        ).exists()
        if not deposit_paid:
            return JsonResponse({"error": "You must pay the deposit for this unit before making rent payments."}, status=400)

        # Rest of the function remains the same...
        try:
            # Generate access token (with Redis caching and retry)
            access_token_cache_key = "mpesa_access_token"
            access_token = cache.get(access_token_cache_key)
            if not access_token:
                try:
                    access_token = generate_access_token()
                except Exception as e:
                    logger.error(f"Access token generation failed, retrying: {str(e)}")
                    # Retry once after a short delay
                    import time
                    time.sleep(1)
                    access_token = generate_access_token()
            # Cache access token for 55 minutes (MPESA tokens expire in 1 hour)
            cache.set(access_token_cache_key, access_token, timeout=3300)
        except Exception as e:
            logger.error(f"Access token generation failed after retry: {str(e)}")
            return JsonResponse({"error": "Payment service temporarily unavailable. Please try again later."}, status=503)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")
        
        # Always use central shortcode for rent payments
        business_shortcode = settings.MPESA_SHORTCODE
        
        # Build payload for Safaricom API
        payload = {
            "BusinessShortCode": business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),  # Ensure whole number for M-Pesa
            "PartyA": request.user.phone_number,
            "PartyB": business_shortcode,
            "PhoneNumber": request.user.phone_number,
            "CallBackURL": settings.MPESA_RENT_CALLBACK_URL,
            "AccountReference": str(payment.id),
            "TransactionDesc": f"Rent for Unit {unit.unit_number}"
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            # Don't fail the payment - mark it as pending for manual processing
            logger.error(f"M-Pesa API request failed: {str(e)}")
            return JsonResponse({
                "message": "Payment initiation received. Please check your phone to complete payment.",
                "payment_id": payment.id
            })
        except json.JSONDecodeError as e:
            logger.error(f"Invalid response from M-Pesa API: {str(e)}")
            return JsonResponse({
                "message": "Payment initiation received. Please check your phone to complete payment.",
                "payment_id": payment.id
            })
        
        if response_data.get("ResponseCode") == "0":
            # Return success immediately without waiting
            return JsonResponse({
                "message": "Payment initiated successfully. Please check your phone to complete payment.",
                "checkout_request_id": response_data.get("CheckoutRequestID"),
                "payment_id": payment.id
            })
        else:
            # M-Pesa returned an error but we don't fail the payment
            error_msg = response_data.get("ResponseDescription", "Unknown error")
            logger.error(f"M-Pesa STK push error: {error_msg}")
            return JsonResponse({
                "message": "Payment initiation received. Please check your phone to complete payment.",
                "payment_id": payment.id,
                "note": "If payment doesn't appear on your phone, please try again in a few minutes."
            })
            
    except Exception as e:
        logger.error(f"Unexpected error in stk_push: {str(e)}")
        return JsonResponse({"error": "Payment service temporarily unavailable. Please try again later."}, status=503)
# ------------------------------
# STK PUSH INITIATION (Landlord Subscription Payment) - UPDATED
# ------------------------------
@csrf_exempt
def stk_push_subscription(request):
    """
    Initiates an M-Pesa STK Push for a landlord's subscription payment.
    - Uses minimal amounts for testing (50 KSH)
    - Better error handling
    """
    try:
        # Get subscription plan from request
        plan = None
        phone_number = None
        
        try:
            if request.method == 'POST':
                try:
                    body = json.loads(request.body.decode('utf-8') or '{}')
                except Exception:
                    body = {}
                plan = body.get('plan') or request.GET.get('plan')
                phone_number = body.get('phone_number')
            else:
                plan = request.GET.get('plan')
        except Exception:
            plan = request.GET.get('plan')
        
        if not plan:
            return JsonResponse({"error": "Plan parameter is required."}, status=400)
        if not phone_number:
            return JsonResponse({"error": "Phone number is required."}, status=400)
        
        # Map plan to amount - MINIMAL AMOUNTS FOR TESTING
        plan_amounts = {
            "starter": 50,      # Only 50 KSH for testing
            "basic": 100,       # Only 100 KSH for testing  
            "professional": 200, # Only 200 KSH for testing
            "onetime": 500,     # Only 500 KSH for testing
        }
        
        if plan not in plan_amounts:
            return JsonResponse({"error": "Invalid plan."}, status=400)
        
        amount = plan_amounts[plan]
        
        # Rate limiting
        rate_limit_key = f"stk_push_subscription_rate_limit:{phone_number}"
        recent_requests = cache.get(rate_limit_key, 0)
        if recent_requests >= 3:
            return JsonResponse({"error": "Too many requests. Please try again later."}, status=429)
        
        cache.set(rate_limit_key, recent_requests + 1, timeout=60)
        
        # Check for duplicate pending subscription payment
        duplicate_key = f"pending_subscription_payment:{phone_number}:{plan}"
        if cache.get(duplicate_key):
            return JsonResponse({"error": "A subscription payment request is already pending."}, status=400)
        
        # Determine user
        user = None
        if request.user.is_authenticated and request.user.user_type == 'landlord':
            user = request.user
        
        # Create a pending subscription payment record
        subscription_payment = SubscriptionPayment.objects.create(
            user=user,
            amount=amount,
            mpesa_receipt_number="",
            subscription_type=plan
        )
        
        # Mark payment as pending in Redis (5-minute expiry)
        cache.set(duplicate_key, subscription_payment.id, timeout=300)
        
        try:
            # Generate access token
            access_token_cache_key = "mpesa_access_token"
            access_token = cache.get(access_token_cache_key)
            if not access_token:
                access_token = generate_access_token()
            cache.set(access_token_cache_key, access_token, timeout=3300)
        except Exception as e:
            print(f"Access token generation warning: {str(e)}")
            try:
                access_token = generate_access_token()
            except Exception as token_error:
                return JsonResponse({"error": "Subscription service temporarily unavailable. Please try again later."}, status=503)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")
        
        # Build payload for Safaricom API
        party_phone = phone_number
        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(amount),
            "PartyA": party_phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": party_phone,
            "CallBackURL": settings.MPESA_SUBSCRIPTION_CALLBACK_URL,
            "AccountReference": str(subscription_payment.id),
            "TransactionDesc": f"Subscription payment for {plan} plan"
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"M-Pesa subscription API request failed: {str(e)}")
            return JsonResponse({
                "message": "Subscription payment initiation received.",
                "payment_id": subscription_payment.id
            })
        
        if response_data.get("ResponseCode") == "0":
            return JsonResponse({
                "message": "Subscription payment initiated successfully.",
                "checkout_request_id": response_data.get("CheckoutRequestID"),
                "payment_id": subscription_payment.id
            })
        else:
            error_msg = response_data.get("ResponseDescription", "Unknown error")
            print(f"M-Pesa subscription STK push error: {error_msg}")
            return JsonResponse({
                "message": "Subscription payment initiation received.",
                "payment_id": subscription_payment.id
            })
            
    except Exception as e:
        print(f"Unexpected error in stk_push_subscription: {str(e)}")
        return JsonResponse({"error": "Subscription service temporarily unavailable. Please try again later."}, status=503)
# ------------------------------
# RENT PAYMENT CALLBACK
# ------------------------------
# In payments/views.py - FIX THE MPESA RENT CALLBACK
@csrf_exempt
def mpesa_rent_callback(request):
    """
    Handles M-Pesa callback for rent payments.
    - Updates Payment status
    - Updates Unit rent balances
    - Initiates B2C disbursement to landlord
    - Invalidates relevant caches
    """
    logger = logging.getLogger(__name__)
    logger.info("🔄 Rent callback received")

    try:
        data = json.loads(request.body.decode("utf-8"))
        logger.info(f"📥 Rent callback data: {json.dumps(data, indent=2)}")

        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        logger.info(f"🔍 Rent callback result code: {result_code}")

        if result_code == 0:  # ✅ Transaction successful
            metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
            logger.info(f"📋 Rent callback metadata items: {len(metadata_items)}")
            metadata = {item["Name"]: item.get("Value") for item in metadata_items}
            logger.info(f"🔧 Raw metadata: {metadata}")

            # Convert amount to Decimal for consistency
            amount_str = metadata.get("Amount")
            amount = None
            if amount_str:
                try:
                    amount = Decimal(amount_str)
                    logger.info(f"💰 Rent callback amount: {amount} (Decimal)")
                except (ValueError, TypeError) as e:
                    logger.error(f"❌ Invalid amount format: {amount_str}, error: {e}")

            receipt = metadata.get("MpesaReceiptNumber")
            payment_id = metadata.get("AccountReference")
            phone = str(metadata.get("PhoneNumber")) if metadata.get("PhoneNumber") else None

            logger.info(f"💰 Rent callback metadata: amount={amount}, receipt={receipt}, payment_id={payment_id}, phone={phone}")

            if payment_id:
                logger.info(f"🔍 Looking for payment with ID: {payment_id}")
                try:
                    payment = Payment.objects.get(id=payment_id, status="Pending")
                    logger.info(f"✅ Found pending rent payment: {payment.id} for tenant {payment.tenant.email}")

                    payment.status = "Success"
                    payment.mpesa_receipt = receipt
                    payment.save()
                    logger.info(f"✅ Payment {payment.id} status updated to Success")

                    # Update unit balances - FIXED: Use Decimal amount
                    unit = payment.unit
                    unit.rent_paid += amount  # Now both are Decimal
                    unit.rent_remaining = max(unit.rent - unit.rent_paid, Decimal('0'))
                    unit.save()
                    logger.info(f"✅ Unit {unit.unit_number} balances updated: paid={unit.rent_paid}, remaining={unit.rent_remaining}")

                    # Invalidate relevant caches
                    cache.delete_many([
                        f"pending_payment:{payment.tenant.id}:{unit.id}",
                        f"payments:tenant:{payment.tenant.id}",
                        f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                        f"rent_summary:{unit.property_obj.landlord.id}",
                        f"unit:{unit.id}:details"
                    ])
                    logger.info(f"🗑️ Cache invalidated for payment {payment.id}")
                    logger.info(f"✅ Rent payment successful: {receipt} for payment {payment_id}")

                    # Initiate B2C disbursement to landlord
                    landlord = unit.property_obj.landlord
                    recipient = landlord.mpesa_till_number or landlord.phone_number
                    logger.info(f"🏦 Initiating B2C disbursement to landlord {landlord.email}, recipient: {recipient}")
                    if recipient:
                        try:
                            b2c_response = initiate_b2c_payment(
                                amount=amount,
                                recipient=recipient,
                                payment_id=payment_id,
                                remarks=f"Rent payment disbursement for Unit {unit.unit_number}"
                            )
                            logger.info(f"✅ B2C disbursement initiated for payment {payment_id}: {b2c_response}")
                        except ValueError as e:
                            logger.error(f"❌ B2C disbursement failed for payment {payment_id}: {str(e)}")
                    else:
                        logger.error(f"❌ No recipient (till number or phone) for landlord {landlord.id}")

                except Payment.DoesNotExist:
                    logger.error(f"❌ Payment with id {payment_id} not found or already processed")
                except Exception as e:
                    logger.error(f"❌ Error updating payment {payment_id}: {e}")
            else:
                logger.warning("⚠️ No payment_id in rent callback, cannot process payment")
        else:
            # ❌ Transaction failed - UPDATE PAYMENT STATUS TO FAILED
            error_msg = body.get("ResultDesc", "Unknown error")
            logger.error(f"❌ Rent transaction failed: {error_msg} (ResultCode: {result_code})")
            # Try to find and update the payment to Failed
            try:
                payment_id = body.get("AccountReference")
                if payment_id:
                    payment = Payment.objects.get(id=payment_id, status="Pending")
                    payment.status = "Failed"
                    payment.save()
                    logger.info(f"✅ Rent payment {payment_id} marked as Failed")
                    # Invalidate caches
                    cache.delete_many([
                        f"pending_payment:{payment.tenant.id}:{payment.unit.id}",
                        f"payments:tenant:{payment.tenant.id}",
                        f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                    ])
                    logger.info(f"🗑️ Cache invalidated for failed payment {payment_id}")
            except Payment.DoesNotExist:
                logger.error(f"Payment with id {payment_id} not found for failure update")
            except Exception as e:
                logger.error(f"Error updating failed payment: {e}")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in rent callback: {e}")
    except Exception as e:
        logger.error("❌ Unexpected error processing rent callback:", exc_info=True)

    # CRITICAL: Always respond with success to Safaricom to acknowledge callback receipt
    logger.info("✅ Responding with success to M-Pesa rent callback")
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
# ------------------------------
# SUBSCRIPTION PAYMENT CALLBACK
# ------------------------------
@csrf_exempt
def mpesa_subscription_callback(request):
    """
    Handles M-Pesa callback for subscription payments.
    - Finds user by phone number
    - Creates/updates subscription payment
    - Updates user subscription
    - Handles duplicate receipts gracefully
    """
    logger = logging.getLogger(__name__)
    logger.info("🔄 Subscription callback received")

    try:
        data = json.loads(request.body.decode("utf-8"))
        logger.info(f"📥 Subscription callback data: {json.dumps(data, indent=2)}")

        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        logger.info(f"🔍 Subscription callback result code: {result_code}")

        if result_code == 0:  # ✅ Transaction successful
            metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
            logger.info(f"📋 Subscription callback metadata items: {len(metadata_items)}")
            metadata = {item["Name"]: item.get("Value") for item in metadata_items}
            logger.info(f"🔧 Raw metadata: {metadata}")

            # Convert amount to Decimal for consistency
            amount_str = metadata.get("Amount")
            amount = None
            if amount_str:
                try:
                    amount = Decimal(amount_str)
                    logger.info(f"💰 Subscription callback amount: {amount} (Decimal)")
                except (ValueError, TypeError) as e:
                    logger.error(f"❌ Invalid amount format: {amount_str}, error: {e}")

            receipt = metadata.get("MpesaReceiptNumber")
            account_reference = metadata.get("AccountReference")
            phone = str(metadata.get("PhoneNumber")) if metadata.get("PhoneNumber") else None

            logger.info(f"💰 Subscription callback metadata: amount={amount}, receipt={receipt}, account_reference={account_reference}, phone={phone}")

            # Helper function to find user by phone with multiple formats
            def find_user_by_phone(phone_str):
                if not phone_str:
                    return None

                phone_variants = [phone_str]

                # Generate all possible phone number formats
                if phone_str.startswith('+254'):
                    phone_variants.extend([
                        phone_str[4:],           # 722714334
                        '0' + phone_str[4:],     # 0722714334
                        phone_str[1:],           # 254722714334
                    ])
                elif phone_str.startswith('254'):
                    phone_variants.extend([
                        '+' + phone_str,         # +254722714334
                        '0' + phone_str[3:],     # 0722714334
                        phone_str[3:],           # 722714334
                    ])
                elif phone_str.startswith('0'):
                    phone_variants.extend([
                        '+254' + phone_str[1:],  # +254722714334
                        '254' + phone_str[1:],   # 254722714334
                        phone_str[1:],           # 722714334
                    ])
                else:
                    # Assume it's local without 0, add variants
                    phone_variants.extend([
                        '+254' + phone_str,      # +254722714334
                        '254' + phone_str,       # 254722714334
                        '0' + phone_str,         # 0722714334
                    ])

                # Remove duplicates
                phone_variants = list(set(phone_variants))
                logger.info(f"🔍 Searching for user with phone variants: {phone_variants}")
                return CustomUser.objects.filter(
                    user_type='landlord',
                    phone_number__in=phone_variants
                ).first()

            # Find user by phone number
            user = find_user_by_phone(phone)
            if not user:
                logger.error(f"❌ No landlord found with phone number: {phone}")
                # Still acknowledge callback but log error
            else:
                logger.info(f"✅ Found user: {user.email} for phone: {phone}")

                # Determine subscription type from amount
                subscription_type = None
                if amount == Decimal('50'):
                    subscription_type = 'starter'
                elif amount == Decimal('100'):
                    subscription_type = 'basic'
                elif amount == Decimal('200'):
                    subscription_type = 'professional'
                elif amount == Decimal('500'):
                    subscription_type = 'onetime'
                else:
                    logger.warning(f"⚠️ Unknown subscription amount: {amount}, cannot determine plan")

                if subscription_type:
                    # Handle duplicate receipts gracefully
                    try:
                        subscription_payment, created = SubscriptionPayment.objects.get_or_create(
                            mpesa_receipt_number=receipt,
                            defaults={
                                'user': user,
                                'amount': amount,
                                'subscription_type': subscription_type,
                            }
                        )

                        if created:
                            logger.info(f"✅ Created new subscription payment: {subscription_payment.id}")
                        else:
                            logger.warning(f"⚠️ Subscription payment with receipt {receipt} already exists, skipping duplicate")

                        # Update or create subscription
                        subscription, sub_created = Subscription.objects.get_or_create(
                            user=user,
                            defaults={
                                'plan': subscription_type,
                                'expiry_date': timezone.now() + timedelta(days=30) if subscription_type != 'onetime' else None
                            }
                        )

                        if not sub_created:
                            # Update existing subscription
                            subscription.plan = subscription_type
                            if subscription_type == 'onetime':
                                subscription.expiry_date = None  # Lifetime
                            else:
                                subscription.expiry_date = timezone.now() + timedelta(days=30)
                            subscription.save()
                            logger.info(f"✅ Updated subscription for user {user.email} to {subscription_type}")
                        else:
                            logger.info(f"✅ Created new subscription for user {user.email}: {subscription_type}")

                        # Invalidate relevant caches
                        cache.delete_many([
                            f"subscription_payments:{user.id}",
                            f"rent_summary:{user.id}",
                        ])
                        logger.info(f"🗑️ Cache invalidated for subscription payment")

                    except Exception as e:
                        logger.error(f"❌ Error processing subscription payment: {e}")
                else:
                    logger.error(f"❌ Could not determine subscription type for amount: {amount}")
        else:
            # Transaction failed
            error_msg = body.get("ResultDesc", "Unknown error")
            logger.error(f"❌ Subscription transaction failed: {error_msg} (ResultCode: {result_code})")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in subscription callback: {e}")
    except Exception as e:
        logger.error("❌ Unexpected error processing subscription callback:", exc_info=True)

    # CRITICAL: Always respond with success to Safaricom to acknowledge callback receipt
    logger.info("✅ Responding with success to M-Pesa subscription callback")
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
# ------------------------------
# RENT PAYMENTS (DRF Views) - CACHED
# ------------------------------
class PaymentListCreateView(generics.ListCreateAPIView):
    """
    GET:
    - Tenants: only see their own rent payments (cached)
    - Landlords: see all rent payments for units in their properties (cached)
    POST:
    - Only tenants can create a new rent payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
       user = self.request.user
       cache_key = f"payments:{user.user_type}:{user.id}"
       # Try to get cached data
       cached_data = cache.get(cache_key)
       if cached_data:
           # Return a queryset-like object (we'll handle this in the serializer)
           return Payment.objects.none()  # Serializer will use cached data
       # If not cached, fetch from database
       if user.user_type == "tenant":
           queryset = Payment.objects.filter(tenant=user).order_by('-transaction_date')
       elif user.user_type == "landlord":
           queryset = Payment.objects.filter(
               unit__property_obj__landlord=user).order_by('-transaction_date')
       else:
           queryset = Payment.objects.none()
       # Cache the results for 5 minutes
       if queryset.exists():
           cache.set(cache_key, PaymentSerializer(queryset, many=True).data, timeout=300)
       return queryset
    def list(self, request, *args, **kwargs):
       # Custom list method to handle cached data
       user = self.request.user
       cache_key = f"payments:{user.user_type}:{user.id}"
       cached_data = cache.get(cache_key)
       if cached_data:
           return Response(cached_data)
       return super().list(request, *args, **kwargs)
    def perform_create(self, serializer):
       if self.request.user.user_type == "tenant":
           payment = serializer.save(tenant=self.request.user)
           # Invalidate cache after creation
           cache.delete(f"payments:tenant:{self.request.user.id}")
           cache.delete(f"payments:landlord:{payment.unit.property_obj.landlord.id}")
       else:
           raise PermissionError("Only tenants can create rent payments.")
class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET:
    - Tenants: can only view their own payment details (cached)
    - Landlords: can view payment details for units in their properties (cached)
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "tenant":
            return Payment.objects.filter(tenant=user)
        elif user.user_type == "landlord":
            return Payment.objects.filter(unit__property_obj__landlord=user)
        return Payment.objects.none()

    def retrieve(self, request, *args, **kwargs):
        payment_id = kwargs.get('pk')
        cache_key = f"payment:{payment_id}:details"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

# ------------------------------
# SUBSCRIPTION PAYMENTS (DRF Views) - CACHED
# ------------------------------
class SubscriptionPaymentListCreateView(generics.ListCreateAPIView):
    """
    GET:
    - Landlords: only see their own subscription payments (cached)
    - Tenants: no access
    POST:
    - Only landlords can create subscription payments
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "landlord":
            return SubscriptionPayment.objects.filter(user=user).order_by('-transaction_date')
        return SubscriptionPayment.objects.none()

    def list(self, request, *args, **kwargs):
        user = self.request.user
        if user.user_type != "landlord":
            return Response({"error": "Only landlords can view subscription payments."}, status=403)
        cache_key = f"subscription_payments:{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

    def perform_create(self, serializer):
        if self.request.user.user_type == "landlord":
            serializer.save(user=self.request.user)
            # Invalidate cache after creation
            cache.delete(f"subscription_payments:{self.request.user.id}")
        else:
            raise PermissionError("Only landlords can make subscription payments.")
class SubscriptionPaymentDetailView(generics.RetrieveAPIView):
    """
    GET:
    - Landlords: can only view their own subscription payment details (cached)
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "landlord":
            return SubscriptionPayment.objects.filter(user=user)
        return SubscriptionPayment.objects.none()

    def retrieve(self, request, *args, **kwargs):
        payment_id = kwargs.get('pk')
        cache_key = f"subscription_payment:{payment_id}:details"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

class RentSummaryView(APIView):
    """
    Provides a financial summary for landlords (cached):
    - Total rent collected across all their properties
    - Total outstanding rent
    - Per-unit breakdown (unit number, tenant, paid, remaining)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.user_type != "landlord":
            return Response({"error": "Only landlords can view rent summaries."}, status=403)
        # Check cache first
        cache_key = f"rent_summary:{user.id}"
        cached_summary = cache.get(cache_key)
        if cached_summary:
            return Response(cached_summary)
        # Get all units owned by this landlord
        units = Unit.objects.filter(property_obj__landlord=user)
        total_collected = 0
        total_outstanding = 0
        unit_breakdown = []
        for unit in units:
            collected = float(unit.rent_paid)
            outstanding = float(unit.rent_remaining)
            total_collected += collected
            total_outstanding += outstanding
            unit_breakdown.append({
                "unit_number": unit.unit_number,
                "tenant": unit.tenant.email if unit.tenant else None,
                "rent": float(unit.rent),
                "rent_paid": collected,
                "rent_remaining": outstanding,
                "is_available": unit.is_available,
            })
        summary = {
            "landlord": user.email,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "units": unit_breakdown,
            "last_updated": timezone.now().isoformat(),
        }
        # Cache for 10 minutes
        cache.set(cache_key, summary, timeout=600)
        return Response(summary)
# ------------------------------
# GENERATE RENT PAYMENTS CSV REPORT
# ------------------------------
class LandLordCSVView(APIView):
    """
    Generate CSV report for landlord with Redis caching for frequent requests
    """
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get(self, request, property_id):
        cache_key = f"landlord_csv:{property_id}:{request.user.id}"
        cached_response = cache.get(cache_key)
        if cached_response:
            response = HttpResponse(cached_response, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="landlord_data.csv"'
            return response
        property = get_object_or_404(Property, pk=property_id)
        # Verify the property belongs to the logged-in landlord
        if property.landlord != request.user:
            return HttpResponse("Unauthorized", status=403)
        units = property.unit_list.all()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="landlord_data.csv"'
        writer = csv.writer(response)
        writer.writerow(['Tenant', 'Unit Number', 'Floor', 'Bedrooms', 'Bathrooms', 'Rent',
                         'Rent Paid', 'Rent Remaining', 'Rent Due Date', 'Deposit', 'Is Available'])
        for unit in units:
            writer.writerow([
                unit.tenant.email if unit.tenant else 'Vacant',
                unit.unit_number,
                unit.floor,
                unit.bedrooms,
                unit.bathrooms,
                unit.rent,
                unit.rent_paid,
                unit.rent_remaining,  # Fixed: was unit.balance
                unit.rent_due_date,
                unit.deposit,
                unit.is_available
            ])
        # Cache the CSV content for 5 minutes (for frequent downloads)
        cache.set(cache_key, response.content, timeout=300)
        return response
class TenantCSVView(APIView):
    """
    Generate CSV report for tenant with Redis caching
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        cache_key = f"tenant_csv:{unit_id}:{request.user.id}"
        cached_response = cache.get(cache_key)
        if cached_response:
            response = HttpResponse(cached_response, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="tenant_data.csv"'
            return response
        unit = get_object_or_404(Unit, pk=unit_id)
        # Verify the unit belongs to the logged-in tenant
        if unit.tenant != request.user:
            return HttpResponse("Unauthorized", status=403)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tenant_data.csv"'
        writer = csv.writer(response)
        writer.writerow(['Property', 'Unit Number', 'Floor', 'Bedrooms', 'Bathrooms',
                         'Rent', 'Rent Paid', 'Rent Remaining', 'Rent Due Date', 'Deposit'])
        writer.writerow([
            unit.property_obj.name,
            unit.unit_number,
            unit.floor,
            unit.bedrooms,
            unit.bathrooms,
            unit.rent,
            unit.rent_paid,
            unit.rent_remaining,  # Fixed: was unit.balance
            unit.rent_due_date,
            unit.deposit
        ])
        # Cache the CSV content for 5 minutes
        cache.set(cache_key, response.content, timeout=300)
        return response
# ------------------------------
# UNIT TYPES LIST (For Tenants to Choose Room Types)
# ------------------------------
class UnitTypeListView(APIView):
    def get(self, request):
        landlord_code = request.query_params.get('landlord_code')
        if landlord_code:
            try:
                landlord = CustomUser.objects.get(
                    landlord_code=landlord_code, user_type='landlord')
                unit_types = UnitType.objects.filter(landlord=landlord)
            except CustomUser.DoesNotExist:
                return Response({'error': 'Invalid landlord code'}, status=400)
        else:
            unit_types = UnitType.objects.all()
        serializer = UnitTypeSerializer(unit_types, many=True)
        return Response(serializer.data)
# ------------------------------
# INITIATE DEPOSIT PAYMENT
# ------------------------------
class InitiateDepositPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unit_id = request.data.get('unit_id')
        if not unit_id:
            return Response({'error': 'unit_id is required'}, status=400)

        try:
            # Allow deposit payment for units that are available OR not assigned to any tenant
            unit = Unit.objects.get(id=unit_id)
            if not unit.is_available and unit.tenant is not None:
                return Response({'error': 'Unit is already occupied by another tenant'}, status=400)
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found'}, status=400)

        amount = unit.deposit

        # Validate amount
        if amount is None or amount <= 0:
            return Response({"error": "Deposit amount is not set or invalid."}, status=400)

        # Allow decimal amounts for deposits (M-Pesa can handle decimals)
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({"error": "Invalid deposit amount format."}, status=400)
        
        # Rate limiting
        rate_limit_key = f"deposit_stk_push_rate_limit:{request.user.id}"
        recent_requests = cache.get(rate_limit_key, 0)
        if recent_requests >= 5:
            return Response({"error": "Too many requests. Please try again later."}, status=429)
        
        cache.set(rate_limit_key, recent_requests + 1, timeout=60)
        
        # Check for duplicate pending payment
        duplicate_key = f"pending_deposit_payment:{request.user.id}:{unit_id}"
        if cache.get(duplicate_key):
            return Response({"error": "A deposit payment request is already pending for this unit."}, status=400)
        
        # Create a pending payment record
        payment = Payment.objects.create(
            tenant=request.user,
            unit=unit,
            payment_type='deposit',
            amount=amount,
            status="Pending"
        )
        
        # Mark payment as pending in Redis (5-minute expiry)
        cache.set(duplicate_key, payment.id, timeout=300)
        
        try:
            # Generate access token
            access_token_cache_key = "mpesa_access_token"
            access_token = cache.get(access_token_cache_key)
            if not access_token:
                access_token = generate_access_token()
            cache.set(access_token_cache_key, access_token, timeout=3300)
        except Exception as e:
            return Response({"error": f"Payment initiation failed: {str(e)}"}, status=400)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")
        
        business_shortcode = settings.MPESA_SHORTCODE

        # Normalize phone number for M-Pesa API
        def normalize_phone_for_mpesa(phone_str):
            """
            Normalize phone number to M-Pesa compatible format.
            M-Pesa expects format: 254XXXXXXXXX (without +)
            Handles various input formats and ensures correct output.
            """
            if not phone_str:
                return phone_str

            # Remove any spaces, hyphens, or other non-digit characters except +
            phone_str = ''.join(c for c in phone_str if c.isdigit() or c == '+')

            # Handle different formats
            if phone_str.startswith('+254'):
                # +254722714334 -> 254722714334
                return phone_str[1:]
            elif phone_str.startswith('254'):
                # Already in correct format: 254722714334
                return phone_str
            elif phone_str.startswith('0'):
                # 0722714334 -> 254722714334
                return '254' + phone_str[1:]
            elif len(phone_str) == 9 and phone_str.isdigit():
                # 722714334 -> 254722714334 (local format without 0)
                return '254' + phone_str
            else:
                # Unknown format, return as-is but remove + if present
                return phone_str.lstrip('+')

        phone_number = normalize_phone_for_mpesa(request.user.phone_number)

        # Build payload for Safaricom API
        payload = {
            "BusinessShortCode": business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),  # Ensure whole number for M-Pesa
            "PartyA": phone_number,
            "PartyB": business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_DEPOSIT_CALLBACK_URL,
            "AccountReference": str(payment.id),
            "TransactionDesc": f"Deposit for Unit {unit.unit_number}"
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )
            response_data = response.json()
            
            if response_data.get("ResponseCode") == "0":
                return Response({
                    "message": "Deposit payment initiated successfully. Please check your phone to complete payment.",
                    "checkout_request_id": response_data.get("CheckoutRequestID"),
                    "payment_id": payment.id
                })
            else:
                # STK push failed - mark payment as failed immediately
                payment.status = "Failed"
                payment.save()
                cache.delete(duplicate_key)
                return Response({
                    "error": "Payment initiation failed: {}".format(
                        response_data.get("ResponseDescription", "Unknown error")
                    )
                }, status=400)
                
        except requests.exceptions.RequestException as e:
            # Network error - mark payment as failed
            payment.status = "Failed"
            payment.save()
            cache.delete(duplicate_key)
            return Response({"error": "Payment service temporarily unavailable. Please try again later."}, status=503)
# ------------------------------
# TRIGGER DEPOSIT CALLBACK (FOR TESTING)
# ------------------------------
class TriggerDepositCallbackView(APIView):
    """
    Manual endpoint to trigger deposit callback for testing.
    Accepts payment_id as query parameter.
    """
    permission_classes = [IsAuthenticated]  # Allow authenticated users for testing

    def post(self, request):
        from django.http import HttpRequest
        import json
        import logging

        logger = logging.getLogger(__name__)

        payment_id = request.query_params.get('payment_id')
        if not payment_id:
            return Response({"error": "payment_id query parameter required"}, status=400)

        try:
            payment = Payment.objects.get(id=payment_id, payment_type='deposit')
        except Payment.DoesNotExist:
            return Response({"error": f"Deposit payment with id {payment_id} not found"}, status=404)

        # Create mock callback data
        mock_callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "mock-request-id",
                    "CheckoutRequestID": "mock-checkout-id",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": str(payment.amount)},
                            {"Name": "MpesaReceiptNumber", "Value": f"TEST{payment_id}"},
                            {"Name": "TransactionDate", "Value": "20231201120000"},
                            {"Name": "PhoneNumber", "Value": payment.tenant.phone_number},
                            {"Name": "AccountReference", "Value": str(payment.id)}
                        ]
                    }
                }
            }
        }

        # Simulate the callback by calling the actual callback function
        mock_request = HttpRequest()
        mock_request.method = 'POST'
        mock_request._body = json.dumps(mock_callback_data).encode('utf-8')

        logger.info(f"🔧 Manually triggering deposit callback for payment {payment_id}")
        response = mpesa_deposit_callback(mock_request)

        return Response({
            "message": f"Deposit callback triggered for payment {payment_id}",
            "mock_data": mock_callback_data,
            "callback_response": response.content.decode('utf-8')
        })

# ------------------------------
# B2C PAYMENT CALLBACK
# ------------------------------
@csrf_exempt
def mpesa_b2c_callback(request):
    """
    Handles M-Pesa callback for B2C disbursements.
    - Logs the result of the disbursement
    - Could update payment records if needed
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        result = data.get("Result", {})
        result_code = result.get("ResultCode")
        result_desc = result.get("ResultDesc")
        if result_code == 0:  # ✅ Disbursement successful
            print(f"✅ B2C disbursement successful: {result_desc}")
        else:
            print(f"❌ B2C disbursement failed: {result_desc}")
    except Exception as e:
        print("Error processing B2C callback:", e)
    # Always respond with success to Safaricom
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

# ------------------------------
# DEPOSIT PAYMENT CALLBACK
# ------------------------------
@csrf_exempt
def mpesa_deposit_callback(request):
    """
    Handles M-Pesa callback for deposit payments.
    ✅ Automatically confirms deposits and assigns tenant to unit
    ✅ No timeout restriction (safe for delayed callbacks)
    ✅ Always acknowledges Safaricom callback with success
    """
    import logging
    from decimal import Decimal
    from django.utils import timezone
    import json

    logger = logging.getLogger(__name__)
    logger.info("🔄 Deposit callback received")

    try:
        # --- Parse callback data ---
        data = json.loads(request.body.decode("utf-8"))
        logger.info(f"📥 Deposit callback payload: {json.dumps(data, indent=2)}")

        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        logger.info(f"🔍 Deposit callback result code: {result_code}")

        if result_code == 0:  # ✅ Transaction successful
            metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
            metadata = {item["Name"]: item.get("Value") for item in metadata_items}
            logger.info(f"🔧 Parsed metadata: {metadata}")

            # Extract values
            amount_str = metadata.get("Amount")
            receipt = metadata.get("MpesaReceiptNumber")
            payment_id = metadata.get("AccountReference")
            phone = str(metadata.get("PhoneNumber")) if metadata.get("PhoneNumber") else None

            # Convert amount safely
            try:
                amount = Decimal(amount_str)
            except Exception:
                amount = Decimal('0')
            logger.info(f"💰 Amount={amount}, Receipt={receipt}, PaymentID={payment_id}, Phone={phone}")

            # --- Update the payment record ---
            if not payment_id:
                logger.error("❌ Missing AccountReference (payment_id) in callback.")
                return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

            try:
                payment = Payment.objects.get(id=payment_id, payment_type="deposit")
            except Payment.DoesNotExist:
                logger.error(f"❌ Payment with id {payment_id} not found.")
                return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

            # Update payment status
            payment.status = "Success"
            payment.mpesa_receipt = receipt
            payment.transaction_date = timezone.now()
            payment.save()
            logger.info(f"✅ Payment {payment.id} marked as Success")

            # --- Assign tenant automatically ---
            unit = payment.unit
            if unit.is_available or not unit.tenant:
                unit.tenant = payment.tenant
                unit.is_available = False
                unit.save()
                logger.info(f"🏠 Tenant {payment.tenant.email} assigned to unit {unit.unit_number}")
            else:
                logger.warning(f"⚠️ Unit {unit.unit_number} already occupied. Skipping assignment.")

            # --- Invalidate caches ---
            cache.delete_many([
                f"pending_deposit_payment:{payment.tenant.id}:{unit.id}",
                f"payments:tenant:{payment.tenant.id}",
                f"payments:landlord:{unit.property_obj.landlord.id}",
                f"rent_summary:{unit.property_obj.landlord.id}",
                f"unit:{unit.id}:details",
                f"property:{unit.property_obj.id}:units"
            ])
            logger.info(f"🗑️ Cache cleared for payment {payment.id}")

        else:
            # ❌ Transaction failed
            error_msg = body.get("ResultDesc", "Unknown error")
            payment_id = body.get("AccountReference")
            logger.error(f"❌ Deposit transaction failed: {error_msg} (Payment ID: {payment_id})")

            if payment_id:
                try:
                    payment = Payment.objects.get(id=payment_id, payment_type="deposit")
                    payment.status = "Failed"
                    payment.save()
                    cache.delete_many([
                        f"pending_deposit_payment:{payment.tenant.id}:{payment.unit.id}",
                        f"payments:tenant:{payment.tenant.id}",
                        f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                    ])
                    logger.info(f"✅ Marked payment {payment_id} as Failed")
                except Payment.DoesNotExist:
                    logger.error(f"Payment {payment_id} not found for failure update")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in deposit callback: {e}")
    except Exception as e:
        logger.exception("❌ Unexpected error in deposit callback")

    # --- Always respond success to Safaricom ---
    logger.info("✅ Acknowledging M-Pesa callback with success")
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

# ------------------------------
# DEPOSIT PAYMENT STATUS VIEW
# ------------------------------
class DepositPaymentStatusView(APIView):
    """
    Allows tenants to check the status of their deposit payment.
    Includes automatic timeout detection (10 minutes).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(
                id=payment_id,
                tenant=request.user,
                payment_type='deposit'
            )
        except Payment.DoesNotExist:
            return Response({"error": "Deposit payment not found"}, status=404)

        # Check for timeout (10 minutes)
        if payment.status == "Pending":
            time_elapsed = timezone.now() - payment.transaction_date
            if time_elapsed.total_seconds() > 600:  # 10 minutes
                payment.status = "Failed"
                payment.save()
                logger.warning(f"Payment {payment.id} timed out after 10 minutes")

                # Invalidate caches
                cache.delete_many([
                    f"pending_deposit_payment:{payment.tenant.id}:{payment.unit.id}",
                    f"payments:tenant:{payment.tenant.id}",
                    f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                ])

        return Response({
            "payment_id": payment.id,
            "status": payment.status,
            "amount": payment.amount,
            "unit_number": payment.unit.unit_number,
            "transaction_date": payment.transaction_date,
            "mpesa_receipt": payment.mpesa_receipt
        })

# ------------------------------
# CLEANUP PENDING PAYMENTS VIEW
# ------------------------------
class CleanupPendingPaymentsView(APIView):
    """
    Admin endpoint to cleanup pending payments older than 10 minutes.
    Marks them as Failed and invalidates relevant caches.
    """
    permission_classes = [IsAuthenticated]  # TODO: Add admin permission

    def post(self, request):
        # Add logger import at the top of the function
        logger = logging.getLogger(__name__)

        # Find all pending payments older than 10 minutes
        cutoff_time = timezone.now() - timedelta(minutes=10)
        pending_payments = Payment.objects.filter(
            status="Pending",
            transaction_date__lt=cutoff_time
        )

        cleaned_count = 0
        for payment in pending_payments:
            payment.status = "Failed"
            payment.save()
            cleaned_count += 1

            # Invalidate relevant caches
            if payment.payment_type == 'deposit':
                cache.delete_many([
                    f"pending_deposit_payment:{payment.tenant.id}:{payment.unit.id}",
                    f"payments:tenant:{payment.tenant.id}",
                    f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                ])
            else:  # rent payment
                cache.delete_many([
                    f"pending_payment:{payment.tenant.id}:{payment.unit.id}",
                    f"payments:tenant:{payment.tenant.id}",
                    f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                ])

        logger.info(f"Cleaned up {cleaned_count} pending payments older than 10 minutes")

        return Response({
            "message": f"Cleaned up {cleaned_count} pending payments",
            "cutoff_time": cutoff_time.isoformat()
        })

# ------------------------------
# SIMULATE DEPOSIT CALLBACK VIEW
# ------------------------------
class SimulateDepositCallbackView(APIView):
    """
    Endpoint to simulate deposit callback for testing purposes.
    Accepts payment_id as query parameter and simulates success/failure.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.query_params.get('payment_id')
        if not payment_id:
            return Response({"error": "payment_id query parameter required"}, status=400)

        try:
            payment = Payment.objects.get(id=payment_id, payment_type='deposit')
        except Payment.DoesNotExist:
            return Response({"error": f"Deposit payment with id {payment_id} not found"}, status=404)

        # Check if callback is within timeout (10 minutes)
        time_elapsed = timezone.now() - payment.transaction_date
        if time_elapsed.total_seconds() > 600:  # 10 minutes
            return Response({"error": "Payment has timed out (10 minutes)"}, status=400)

        # Simulate successful callback
        mock_callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "mock-request-id",
                    "CheckoutRequestID": "mock-checkout-id",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": str(payment.amount)},
                            {"Name": "MpesaReceiptNumber", "Value": f"SIM{payment_id}"},
                            {"Name": "TransactionDate", "Value": timezone.now().strftime("%Y%m%d%H%M%S")},
                            {"Name": "PhoneNumber", "Value": payment.tenant.phone_number},
                            {"Name": "AccountReference", "Value": str(payment.id)}
                        ]
                    }
                }
            }
        }

        # Create mock request to call the actual callback function
        from django.http import HttpRequest
        mock_request = HttpRequest()
        mock_request.method = 'POST'
        mock_request._body = json.dumps(mock_callback_data).encode('utf-8')

        logger.info(f"🔧 Simulating deposit callback for payment {payment_id}")
        response = mpesa_deposit_callback(mock_request)

        return Response({
            "message": f"Deposit callback simulated for payment {payment_id}",
            "mock_data": mock_callback_data,
            "callback_response": response.content.decode('utf-8')
        })
