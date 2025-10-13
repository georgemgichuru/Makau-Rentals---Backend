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
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from accounts.models import CustomUser, Subscription, Property, Unit, UnitType
from accounts.permissions import require_tenant_subscription, require_subscription
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
# STK PUSH INITIATION (Tenant Rent Payment)
# ------------------------------


@login_required
@require_tenant_subscription
def stk_push(request, unit_id):
   """
   Initiates an M-Pesa STK Push for a tenant's rent payment.
   - Validates payment amount: positive, <=500000, multiple of rent, <= rent*12
   - Creates a pending Payment record
   - Calls Safaricom STK Push API
   - Uses Redis for rate limiting and duplicate request prevention
   """
   try:
    if request.method != 'POST':
     return JsonResponse({"error": "POST method required."}, status=405)
    # Get amount from POST data
    amount_str = request.POST.get('amount')
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
    # Ensure the unit belongs to the logged-in tenant
    unit = Unit.objects.get(id=unit_id, tenant=request.user)
    # Validate amount
    if amount <= 0:
     return JsonResponse({"error": "Amount must be positive."}, status=400)
    if amount > 500000:
     return JsonResponse({"error": "Amount cannot exceed 500,000."}, status=400)
    if amount % unit.rent != 0:
     return JsonResponse({"error": "Amount must be a multiple of the monthly rent."}, status=400)
    max_amount = unit.rent * 12
    if amount > max_amount:
     return JsonResponse({"error": "Amount cannot exceed one year's rent."}, status=400)
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
    try:
        # Generate access token (with Redis caching)
        access_token_cache_key = "mpesa_access_token"
        access_token = cache.get(access_token_cache_key)
        if not access_token:
         access_token = generate_access_token()
        # Cache access token for 55 minutes (MPESA tokens expire in 1 hour)
        cache.set(access_token_cache_key, access_token, timeout=3300)
    except ValueError as e:
        return JsonResponse({"error": f"Payment initiation failed: Invalid M-Pesa credentials. {str(e)}"}, status=400)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
     (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
    ).decode("utf-8")
    # Always use central shortcode for rent payments (no landlord till dependency)
    business_shortcode = settings.MPESA_SHORTCODE
    # Build payload for Safaricom API
    payload = {
     "BusinessShortCode": business_shortcode,
     "Password": password,
     "Timestamp": timestamp,
     "TransactionType": "CustomerPayBillOnline",
     "Amount": str(payment.amount),  # Rent due
     # Tenant phone number (must be in 2547XXXXXXX format)
     "PartyA": request.user.phone_number,
     "PartyB": business_shortcode,
     "PhoneNumber": request.user.phone_number,
     "CallBackURL": settings.MPESA_RENT_CALLBACK_URL,  # Rent callback endpoint
     "AccountReference": str(payment.id),  # Unique reference for reconciliation
     "TransactionDesc": f"Rent for Unit {unit.unit_number}"
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(
     "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
     json=payload,
     headers=headers
    )
    response_data = response.json()
    if response_data.get("ResponseCode") == "0":
        # Wait up to 30 seconds for payment to complete
        for _ in range(30):
            time.sleep(1)
            payment.refresh_from_db()
            if payment.status == "Success":
                return JsonResponse({"message": "Payment successful", "receipt": payment.mpesa_receipt})
        # Timeout: set to Failed
        payment.status = "Failed"
        payment.save()
        return JsonResponse({"error": "Payment timed out. Please try again."})
    else:
        return JsonResponse(response_data)
   except Unit.DoesNotExist:
    return JsonResponse({"error": "Unit not found or not assigned to you"}, status=404)
   except Exception as e:
    return JsonResponse({"error": f"Payment initiation failed: {str(e)}"}, status=500)
# ------------------------------
# STK PUSH INITIATION (Landlord Subscription Payment)
# ------------------------------
@csrf_exempt
def stk_push_subscription(request):
    """
    Initiates an M-Pesa STK Push for a landlord's subscription payment.
    - Creates a pending SubscriptionPayment record
    - Calls Safaricom STK Push API using central shortcode
    - Uses Redis for rate limiting and duplicate request prevention
    """
    try:
       # Get subscription plan from request (allow POST JSON or query param)
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
       # Map plan to amount
       # Prices (KES): Starter (up to 10 units) - 2000/month, Basic (10-50) - 5000/month,
       # Professional (50-100) - 10000/month (assumed by developer), One-time - 40000
       plan_amounts = {
           "starter": 2000,
           "basic": 5000,
           "professional": 10000,
           "onetime": 40000,
       }
       if plan not in plan_amounts:
           return JsonResponse({"error": "Invalid plan."}, status=400)
       amount = plan_amounts[plan]
       # Rate limiting: Check if phone has made too many requests
       rate_limit_key = f"stk_push_subscription_rate_limit:{phone_number}"
       recent_requests = cache.get(rate_limit_key, 0)
       if recent_requests >= 3:  # Max 3 requests per minute
           return JsonResponse({"error": "Too many requests. Please try again later."}, status=429)
       # Update rate limit counter
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
           mpesa_receipt_number="",  # Will be updated on callback
           subscription_type=plan
       )
       # Mark payment as pending in Redis (5-minute expiry)
       cache.set(duplicate_key, subscription_payment.id, timeout=300)
       try:
           # Generate access token (with Redis caching)
           access_token_cache_key = "mpesa_access_token"
           access_token = cache.get(access_token_cache_key)
           if not access_token:
               access_token = generate_access_token()
           # Cache access token for 55 minutes (MPESA tokens expire in 1 hour)
           cache.set(access_token_cache_key, access_token, timeout=3300)
       except ValueError as e:
           return JsonResponse({"error": f"Payment initiation failed: Invalid M-Pesa credentials. {str(e)}"}, status=400)
       timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
       password = base64.b64encode(
           (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
       ).decode("utf-8")
       # Build payload for Safaricom API (using central shortcode)
       # If a phone_number was included in the request body, prefer it for PartyA/PhoneNumber
       party_phone = phone_number or request.user.phone_number
       payload = {
           "BusinessShortCode": settings.MPESA_SHORTCODE,
           "Password": password,
           "Timestamp": timestamp,
           "TransactionType": "CustomerPayBillOnline",
           "Amount": str(amount),
           "PartyA": party_phone,
           "PartyB": settings.MPESA_SHORTCODE,
           "PhoneNumber": party_phone,
           # Subscription callback endpoint
           "CallBackURL": settings.MPESA_SUBSCRIPTION_CALLBACK_URL,
           "AccountReference": str(subscription_payment.id),  # Unique reference
           "TransactionDesc": f"Subscription payment for {plan} plan"
       }
       headers = {"Authorization": f"Bearer {access_token}"}
       response = requests.post(
           "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
           json=payload,
           headers=headers
       )
       response_data = response.json()
       if response_data.get("ResponseCode") == "0":
           # Wait up to 30 seconds for payment to complete
           for _ in range(30):
               time.sleep(1)
               subscription_payment.refresh_from_db()
               if subscription_payment.mpesa_receipt_number:
                   return JsonResponse({"message": "Subscription payment successful", "receipt": subscription_payment.mpesa_receipt_number})
           # Timeout: return error
           return JsonResponse({"error": "Subscription payment timed out. Please try again."})
       else:
           return JsonResponse(response_data)
    except Exception as e:
       return JsonResponse({"error": f"Subscription payment initiation failed: {str(e)}"}, status=500)
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
    time.sleep(30)  # Await 30 seconds as requested
    try:
       data = json.loads(request.body.decode("utf-8"))
       body = data.get("Body", {}).get("stkCallback", {})
       result_code = body.get("ResultCode")
       if result_code == 0:  # ✅ Transaction successful
           metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
           metadata = {item["Name"]: item.get("Value") for item in metadata_items}
           # FIXED: Convert float to Decimal properly
           amount = Decimal(str(metadata.get("Amount")))  # Convert to string first
           receipt = metadata.get("MpesaReceiptNumber")
           payment_id = metadata.get("AccountReference")
           if payment_id:
               try:
                   payment = Payment.objects.get(id=payment_id, status="Pending")
                   payment.status = "Success"
                   payment.mpesa_receipt = receipt
                   payment.save()
                   # Update unit balances - FIXED: Use Decimal amount
                   unit = payment.unit
                   unit.rent_paid += amount  # Now both are Decimal
                   unit.rent_remaining = max(unit.rent - unit.rent_paid, Decimal('0'))
                   unit.save()
                   # Invalidate relevant caches
                   cache.delete_many([
                       f"pending_payment:{payment.tenant.id}:{unit.id}",
                       f"payments:tenant:{payment.tenant.id}",
                       f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                       f"rent_summary:{unit.property_obj.landlord.id}",
                       f"unit:{unit.id}:details"
                   ])
                   print(f"✅ Rent payment successful: {receipt} for payment {payment_id}")

                   # Initiate B2C disbursement to landlord
                   landlord = unit.property_obj.landlord
                   recipient = landlord.mpesa_till_number or landlord.phone_number
                   if recipient:
                       try:
                           b2c_response = initiate_b2c_payment(
                               amount=amount,
                               recipient=recipient,
                               payment_id=payment_id,
                               remarks=f"Rent payment disbursement for Unit {unit.unit_number}"
                           )
                           print(f"✅ B2C disbursement initiated for payment {payment_id}: {b2c_response}")
                       except ValueError as e:
                           print(f"❌ B2C disbursement failed for payment {payment_id}: {str(e)}")
                   else:
                       print(f"❌ No recipient (till number or phone) for landlord {landlord.id}")

               except Payment.DoesNotExist:
                   print(f"Payment with id {payment_id} not found or already processed")
           else:
               # ❌ Transaction failed
               error_msg = body.get("ResultDesc", "Unknown error")
               print(f"❌ Rent transaction failed: {error_msg}")
       else:
           # ❌ Transaction failed
           error_msg = body.get("ResultDesc", "Unknown error")
           print(f"❌ Rent transaction failed: {error_msg}")
    except Exception as e:
       print("Error processing rent callback:", e)
    # Always respond with success to Safaricom
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
# ------------------------------
# SUBSCRIPTION PAYMENT CALLBACK
# ------------------------------
# In payments/views.py - FIX THE SUBSCRIPTION CALLBACK
@csrf_exempt
def mpesa_subscription_callback(request):
    """
    Handles M-Pesa callback for subscription payments.
    - Creates SubscriptionPayment record
    - Updates landlord's Subscription plan and expiry
    - Invalidates subscription caches
    """
    time.sleep(30)  # Await 30 seconds as requested
    try:
      data = json.loads(request.body.decode("utf-8"))
      body = data.get("Body", {}).get("stkCallback", {})
      result_code = body.get("ResultCode")
      if result_code == 0:  # ✅ Transaction successful
          metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
          metadata = {item["Name"]: item.get("Value") for item in metadata_items}
          # FIXED: Convert amount to proper type
          amount = int(metadata.get("Amount"))
          receipt = metadata.get("MpesaReceiptNumber")
          # For STK Push, this is the payment ID
          account_reference = metadata.get("AccountReference")
          # Helper function to find user by phone with multiple formats
          def find_user_by_phone(phone_str):
              if not phone_str:
                  return None
              phone_variants = [phone_str]
              if phone_str.startswith('+254'):
                  phone_variants.extend([
                      phone_str[4:],  # 722714334
                      '0' + phone_str[4:],  # 0722714334
                      phone_str[1:],  # 254722714334
                  ])
              elif phone_str.startswith('254'):
                  phone_variants.extend([
                      '+' + phone_str,  # +254722714334
                      '0' + phone_str[3:],  # 0722714334
                      phone_str[3:],  # 722714334
                  ])
              elif phone_str.startswith('0'):
                  phone_variants.extend([
                      '+254' + phone_str[1:],  # +254722714334
                      '254' + phone_str[1:],  # 254722714334
                      phone_str[1:],  # 722714334
                  ])
              else:
                  # Assume it's local without 0, add variants
                  phone_variants.extend([
                      '+254' + phone_str,  # +254722714334
                      '254' + phone_str,  # 254722714334
                      '0' + phone_str,  # 0722714334
                  ])
              return CustomUser.objects.filter(user_type='landlord', phone_number__in=phone_variants).first()
          
          if account_reference:
              # Try to find pending subscription payment by ID
              try:
                  subscription_payment = SubscriptionPayment.objects.get(
                      id=account_reference, mpesa_receipt_number="")
                  subscription_payment.mpesa_receipt_number = receipt
                  subscription_payment.save()
                  user = subscription_payment.user
                  # If user is None, try to assign based on phone
                  if not user:
                      phone = metadata.get("PhoneNumber")
                      user = find_user_by_phone(phone)
                      if user:
                          subscription_payment.user = user
                          subscription_payment.save()
                  # Clear pending cache
                  if user:
                      cache.delete(
                          f"pending_subscription_payment:{user.id}:{subscription_payment.subscription_type}")
              except SubscriptionPayment.DoesNotExist:
                  # Fallback to old method if no pending payment found
                  phone = metadata.get("PhoneNumber")
                  user = find_user_by_phone(phone)
                  if not user:
                      return JsonResponse({'error': 'Landlord not found'}, status=404)
                  # Map amount to subscription type and duration
                  plans = {
                      2000: ("starter", timedelta(days=30)),
                      5000: ("basic", timedelta(days=30)),
                      10000: ("professional", timedelta(days=30)),
                      40000: ("onetime", None),  # One-time payment, no expiry
                  }
                  if amount not in plans:
                      return JsonResponse({'error': 'Invalid amount'}, status=400)
                  sub_type, duration = plans[amount]
                  # Save subscription payment
                  subscription_payment = SubscriptionPayment.objects.create(
                      user=user,
                      amount=amount,
                      mpesa_receipt_number=receipt,
                      subscription_type=sub_type
                  )
          else:
              # Old method without account reference
              phone = metadata.get("PhoneNumber")
              user = find_user_by_phone(phone)
              if not user:
                  return JsonResponse({'error': 'Landlord not found'}, status=404)
              # Map amount to subscription type and duration
              plans = {
                  2000: ("starter", timedelta(days=30)),
                  5000: ("basic", timedelta(days=30)),
                  10000: ("professional", timedelta(days=30)),
                  40000: ("onetime", None),  # One-time payment, no expiry
              }
              if amount not in plans:
                  return JsonResponse({'error': 'Invalid amount'}, status=400)
              sub_type, duration = plans[amount]
              # Save subscription payment
              subscription_payment = SubscriptionPayment.objects.create(
                  user=user,
                  amount=amount,
                  mpesa_receipt_number=receipt,
                  subscription_type=sub_type
              )
          
          # Check if user was found
          if not user:
              return JsonResponse({'error': 'Landlord not found'}, status=404)
          
          # Update or create subscription
          subscription, _ = Subscription.objects.get_or_create(user=user)
          subscription.plan = subscription_payment.subscription_type
          subscription.start_date = timezone.now()
          if subscription_payment.subscription_type == "onetime":
              subscription.expiry_date = None
          else:
              duration_map = {
                  "starter": timedelta(days=30),
                  "basic": timedelta(days=30),
                  "professional": timedelta(days=30),
              }
              subscription.expiry_date = timezone.now() + duration_map.get(
                  subscription_payment.subscription_type, timedelta(days=30)
              )
          subscription.save()
          
          # Invalidate subscription-related caches
          cache.delete_many([
              f"subscription:{user.id}",
              f"subscription_payments:{user.id}",
              f"user:{user.id}:subscription_status"
          ])
          print(f"✅ Subscription payment successful: {receipt} for user {user.email}")
      else:
          error_msg = body.get("ResultDesc", "Unknown error")
          print(f"❌ Subscription transaction failed: {error_msg}")
    except Exception as e:
      print("Error processing subscription callback:", e)
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
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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
        try:
            unit = Unit.objects.get(id=unit_id, is_available=True)
        except Unit.DoesNotExist:
            return Response({'error': 'Invalid unit or not available'}, status=400)
        amount = unit.deposit
        # Rate limiting: Check if user has made too many requests
        rate_limit_key = f"deposit_stk_push_rate_limit:{request.user.id}"
        recent_requests = cache.get(rate_limit_key, 0)
        if recent_requests >= 5:  # Max 5 requests per minute
            return Response({"error": "Too many requests. Please try again later."}, status=429)
        # Update rate limit counter
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
            # Generate access token (with Redis caching)
            access_token_cache_key = "mpesa_access_token"
            access_token = cache.get(access_token_cache_key)
            if not access_token:
                access_token = generate_access_token()
            # Cache access token for 55 minutes (MPESA tokens expire in 1 hour)
            cache.set(access_token_cache_key, access_token, timeout=3300)
        except ValueError as e:
            return Response({"error": f"Payment initiation failed: Invalid M-Pesa credentials. {str(e)}"}, status=400)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")
        # Always use central shortcode for deposit payments (no landlord till dependency)
        business_shortcode = settings.MPESA_SHORTCODE
        # Build payload for Safaricom API
        payload = {
            "BusinessShortCode": business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(payment.amount),  # Deposit due
            # Tenant phone number (must be in 2547XXXXXXX format)
            "PartyA": request.user.phone_number,
            "PartyB": business_shortcode,
            "PhoneNumber": request.user.phone_number,
            "CallBackURL": settings.MPESA_DEPOSIT_CALLBACK_URL,  # Deposit callback endpoint
            "AccountReference": str(payment.id),  # Unique reference for reconciliation
            "TransactionDesc": f"Deposit for Unit {unit.unit_number}"
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )
        response_data = response.json()
        if response_data.get("ResponseCode") == "0":
            # Wait up to 30 seconds for payment to complete
            for _ in range(30):
                time.sleep(1)
                payment.refresh_from_db()
                if payment.status == "Success":
                    return Response({"message": "Deposit payment successful", "receipt": payment.mpesa_receipt})
            # Timeout: set to Failed
            payment.status = "Failed"
            payment.save()
            return Response({"error": "Deposit payment timed out. Please try again."})
        else:
            return Response(response_data)
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
    - Updates Payment status
    - Invalidates relevant caches
    """
    time.sleep(30)  # Await 30 seconds as requested
    try:
        data = json.loads(request.body.decode("utf-8"))
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        if result_code == 0:  # ✅ Transaction successful
            metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
            metadata = {item["Name"]: item.get("Value") for item in metadata_items}
            amount = metadata.get("Amount")
            receipt = metadata.get("MpesaReceiptNumber")
            payment_id = metadata.get("AccountReference")
            if payment_id:
                try:
                    payment = Payment.objects.get(
                        id=payment_id, status="Pending", payment_type="deposit")
                    payment.status = "Success"
                    payment.mpesa_receipt = receipt
                    payment.save()
                    # Invalidate relevant caches
                    cache.delete_many([
                        f"pending_deposit_payment:{payment.tenant.id}:{payment.unit.id}",
                        f"payments:tenant:{payment.tenant.id}",
                        f"payments:landlord:{payment.unit.property_obj.landlord.id}",
                        f"rent_summary:{payment.unit.property_obj.landlord.id}",
                        f"unit:{payment.unit.id}:details"
                    ])
                    print(f"✅ Deposit payment successful: {receipt} for payment {payment_id}")
                except Payment.DoesNotExist:
                    print(f"Payment with id {payment_id} not found or already processed")
            else:
                # Transaction failed
                error_msg = body.get("ResultDesc", "Unknown error")
                print(f"❌ Deposit transaction failed: {error_msg}")
        else:
            # Transaction failed
            error_msg = body.get("ResultDesc", "Unknown error")
            print(f"❌ Deposit transaction failed: {error_msg}")
    except Exception as e:
        print("Error processing deposit callback:", e)
    # Always respond with success to Safaricom
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
