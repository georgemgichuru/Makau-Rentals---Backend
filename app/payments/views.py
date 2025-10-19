from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum, Q
from django.http import HttpResponse
import json
import requests
from decimal import Decimal
from datetime import datetime, timedelta
import csv
import io
import base64
import logging

from accounts.models import CustomUser, Unit, UnitType, Property, Subscription
from .models import Payment, SubscriptionPayment
from .generate_token import generate_access_token
from .serializers import PaymentSerializer, SubscriptionPaymentSerializer

logger = logging.getLogger(__name__)

# Add this function after imports and before other functions
def validate_mpesa_payment(phone_number, amount):
    """
    Validate payment parameters before initiating STK push
    """
    # Validate phone number format
    if not phone_number or not isinstance(phone_number, str):
        return False, "Phone number is required"
    
    if not phone_number.startswith('254') or len(phone_number) != 12:
        return False, "Phone number must be in format 254XXXXXXXXX"
    
    # Validate phone number contains only digits after 254
    if not phone_number[3:].isdigit():
        return False, "Phone number must contain only digits"
    
    # Validate amount
    if amount <= 0:
        return False, "Amount must be greater than 0"
    
    if amount > 150000:  # M-Pesa transaction limit
        return False, "Amount exceeds M-Pesa transaction limit (KES 150,000)"
    
    return True, "Valid"

# ------------------------------
# M-PESA STK PUSH FUNCTIONS
# ------------------------------
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stk_push(request, unit_id):
    """
    Initiate REAL STK push for rent payment
    """
    try:
        unit = get_object_or_404(Unit, id=unit_id)
        tenant = request.user

        # Validate tenant owns the unit
        if unit.tenant != tenant:
            return Response({"error": "You don't have permission to pay for this unit"}, status=status.HTTP_403_FORBIDDEN)

        # Check if rent is already paid
        if unit.rent_remaining <= 0:
            return Response({"error": "Rent is already paid for this unit"}, status=status.HTTP_400_BAD_REQUEST)

        amount = unit.rent_remaining
        phone_number = tenant.phone_number

        if not phone_number:
            return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate phone number format (should be 254XXXXXXXXX)
        if not phone_number.startswith('254'):
            return Response({"error": "Phone number must be in format 254XXXXXXXXX"}, status=status.HTTP_400_BAD_REQUEST)

         # ✅ ADD VALIDATION HERE
        is_valid, validation_message = validate_mpesa_payment(phone_number, amount)
        if not is_valid:
            return Response({"error": validation_message}, status=status.HTTP_400_BAD_REQUEST)

        # Generate access token
        access_token = generate_access_token()
        if not access_token:
            return Response({"error": "Failed to generate M-Pesa access token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare STK push request for PRODUCTION
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode('utf-8')
        ).decode('utf-8')

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_RENT_CALLBACK_URL,
            "AccountReference": f"RENT-{unit.unit_code}",
            "TransactionDesc": f"Rent payment for {unit.unit_number}"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Use production URL
        if settings.MPESA_ENV == "sandbox":
            url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        else:
            url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ResponseCode") == "0":
            # Create pending payment record
            payment = Payment.objects.create(
                tenant=tenant,
                unit=unit,
                amount=amount,
                status="Pending",
                payment_type="rent",
                mpesa_checkout_request_id=response_data["CheckoutRequestID"]
            )

            # Cache checkout request ID for callback
            cache.set(f"stk_{response_data['CheckoutRequestID']}", {
                "payment_id": payment.id,
                "unit_id": unit.id,
                "amount": float(amount),
                "tenant_id": tenant.id
            }, timeout=300)  # 5 minutes

            logger.info(f"STK push initiated for payment {payment.id}, amount {amount}, phone {phone_number}")

            return Response({
                "success": True,
                "message": "STK push initiated successfully",
                "checkout_request_id": response_data["CheckoutRequestID"],
                "payment_id": payment.id
            })

        else:
            logger.error(f"STK push failed: {response_data}")
            return Response({
                "error": "Failed to initiate STK push",
                "details": response_data.get('errorMessage', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"STK push error: {str(e)}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stk_push_subscription(request):
    """
    Initiate STK push for subscription payment
    """
    try:
        user = request.user
        plan = request.data.get('plan')
        phone_number = request.data.get('phone_number')

        if not plan or not phone_number:
            return Response({"error": "Plan and phone number are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate plan
        plan_amounts = {
            'starter': 1000,
            'basic': 2000,
            'professional': 3000
        }

        if plan not in plan_amounts:
            return Response({"error": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        amount = plan_amounts[plan]

        # ✅ ADD VALIDATION HERE
        is_valid, validation_message = validate_mpesa_payment(phone_number, amount)
        if not is_valid:
            return Response({"error": validation_message}, status=status.HTTP_400_BAD_REQUEST)

        # Generate access token
        access_token = generate_access_token()
        if not access_token:
            return Response({"error": "Failed to generate M-Pesa access token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare STK push request
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_SUBSCRIPTION_CALLBACK_URL,
            "AccountReference": f"Subscription-{user.id}",
            "TransactionDesc": f"Subscription payment for {plan} plan"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Make STK push request
        if settings.MPESA_ENV == "sandbox":
            url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        else:
            url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ResponseCode") == "0":
            # Create pending subscription payment record
            subscription_payment = SubscriptionPayment.objects.create(
                user=user,
                amount=Decimal(amount),
                subscription_type=plan,
                status="Pending"
            )

            # Cache checkout request ID for callback
            cache.set(f"stk_sub_{response_data['CheckoutRequestID']}", {
                "subscription_payment_id": subscription_payment.id,
                "user_id": user.id,
                "plan": plan,
                "amount": amount
            }, timeout=300)  # 5 minutes

            return Response({
                "success": True,
                "message": "Subscription STK push initiated successfully",
                "checkout_request_id": response_data["CheckoutRequestID"],
                "subscription_payment_id": subscription_payment.id
            })

        else:
            return Response({
                "error": "Failed to initiate subscription STK push",
                "details": response_data
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------------
# M-PESA CALLBACK FUNCTIONS
# ------------------------------

@csrf_exempt
def mpesa_rent_callback(request):
    """
    Handle M-Pesa rent payment callback
    """
    try:
        callback_data = json.loads(request.body)

        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})

        if stk_callback.get("ResultCode") == 0:
            # Successful payment
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

            mpesa_receipt = None
            amount = None

            for item in callback_metadata:
                if item["Name"] == "MpesaReceiptNumber":
                    mpesa_receipt = item["Value"]
                elif item["Name"] == "Amount":
                    amount = item["Value"]

            checkout_request_id = stk_callback.get("CheckoutRequestID")

            # Get cached payment data
            cached_data = cache.get(f"stk_{checkout_request_id}")
            if cached_data:
                payment = Payment.objects.get(id=cached_data["payment_id"])
                payment.status = "Success"
                payment.mpesa_receipt = mpesa_receipt
                payment.save()

                # Update unit rent_paid
                unit = payment.unit
                unit.rent_paid += Decimal(amount)
                unit.save()

                cache.delete(f"stk_{checkout_request_id}")

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Error"})


@csrf_exempt
def mpesa_subscription_callback(request):
    """
    Handle M-Pesa subscription payment callback
    """
    try:
        callback_data = json.loads(request.body)

        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})

        if stk_callback.get("ResultCode") == 0:
            # Successful payment
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

            mpesa_receipt = None
            amount = None

            for item in callback_metadata:
                if item["Name"] == "MpesaReceiptNumber":
                    mpesa_receipt = item["Value"]
                elif item["Name"] == "Amount":
                    amount = item["Value"]

            checkout_request_id = stk_callback.get("CheckoutRequestID")

            # Get cached subscription payment data
            cached_data = cache.get(f"stk_sub_{checkout_request_id}")
            if cached_data:
                subscription_payment = SubscriptionPayment.objects.get(id=cached_data["subscription_payment_id"])
                subscription_payment.status = "Success"
                subscription_payment.mpesa_receipt_number = mpesa_receipt
                subscription_payment.save()

                # Update user subscription
                user = subscription_payment.user
                subscription = user.subscription
                subscription.plan = subscription_payment.subscription_type
                subscription.expiry_date = timezone.now() + timedelta(days=30)
                subscription.save()

                cache.delete(f"stk_sub_{checkout_request_id}")

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Error"})


@csrf_exempt
def mpesa_b2c_callback(request):
    """
    Handle M-Pesa B2C payment callback
    """
    try:
        callback_data = json.loads(request.body)
        logger.info(f"B2C callback received: {callback_data}")

        result = callback_data.get("Result", {})

        if result.get("ResultCode") == 0:
            # Successful B2C payment
            result_parameters = result.get("ResultParameters", {}).get("ResultParameter", [])

            transaction_receipt = None
            transaction_amount = None
            conversation_id = result.get("ConversationID")

            # Extract relevant parameters
            for param in result_parameters:
                if param["Key"] == "TransactionReceipt":
                    transaction_receipt = param["Value"]
                elif param["Key"] == "TransactionAmount":
                    transaction_amount = param["Value"]

            # Get cached B2C payment data if exists
            cached_data = cache.get(f"b2c_{conversation_id}")
            if cached_data:
                # Update payment status or perform business logic here
                # For example, mark disbursement as successful
                logger.info(f"B2C payment successful: Receipt {transaction_receipt}, Amount {transaction_amount}")
                cache.delete(f"b2c_{conversation_id}")
            else:
                logger.info(f"B2C payment successful (no cached data): Receipt {transaction_receipt}, Amount {transaction_amount}")

        else:
            # Failed B2C payment
            logger.error(f"B2C payment failed: {result.get('ResultDesc')}")

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        logger.error(f"B2C callback error: {str(e)}")
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Error"})


@csrf_exempt
def mpesa_deposit_callback(request):
    """
    Handle M-Pesa deposit payment callback
    """
    try:
        callback_data = json.loads(request.body)
        logger.info(f"Deposit callback received: {callback_data}")

        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})

        if stk_callback.get("ResultCode") == 0:
            # Successful payment
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

            mpesa_receipt = None
            amount = None

            for item in callback_metadata:
                if item["Name"] == "MpesaReceiptNumber":
                    mpesa_receipt = item["Value"]
                elif item["Name"] == "Amount":
                    amount = item["Value"]

            checkout_request_id = stk_callback.get("CheckoutRequestID")

            # Get cached deposit payment data
            cached_data = cache.get(f"stk_deposit_{checkout_request_id}")
            if cached_data:
                payment = Payment.objects.get(id=cached_data["payment_id"])
                payment.status = "Success"
                payment.mpesa_receipt = mpesa_receipt
                payment.save()

                # Mark unit as occupied
                unit = payment.unit
                unit.is_available = False
                unit.save()

                cache.delete(f"stk_deposit_{checkout_request_id}")
                logger.info(f"Deposit payment successful: {payment.id}")

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        logger.error(f"Deposit callback error: {str(e)}")
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Error"})


# ------------------------------
# DRF CLASS-BASED VIEWS
# ------------------------------

class PaymentListCreateView(generics.ListCreateAPIView):
    """
    List and create rent payments
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Payment.objects.filter(tenant=user)
        elif user.user_type == 'landlord':
            # Landlords can see payments for their properties
            return Payment.objects.filter(unit__property_obj__landlord=user)
        return Payment.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user)


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete rent payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Payment.objects.filter(tenant=user)
        elif user.user_type == 'landlord':
            return Payment.objects.filter(unit__property_obj__landlord=user)
        return Payment.objects.none()


class SubscriptionPaymentListCreateView(generics.ListCreateAPIView):
    """
    List and create subscription payments
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubscriptionPayment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriptionPaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete subscription payment
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubscriptionPayment.objects.filter(user=self.request.user)


class RentSummaryView(APIView):
    """
    Get rent summary for landlord
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type != 'landlord':
            return Response({"error": "Only landlords can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)

        # Calculate total collected and outstanding rent
        properties = Property.objects.filter(landlord=user)
        units = Unit.objects.filter(property_obj__in=properties)

        total_collected = Payment.objects.filter(
            unit__in=units,
            status='Success'
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_outstanding = units.aggregate(
            outstanding=Sum('rent_remaining')
        )['outstanding'] or 0

        return Response({
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "properties_count": properties.count(),
            "units_count": units.count()
        })


class UnitTypeListView(generics.ListAPIView):
    """
    List unit types for landlord
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UnitType.objects.filter(landlord=self.request.user)


class InitiateDepositPaymentView(APIView):
    """
    Initiate REAL deposit payment for unit
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = get_object_or_404(Unit, id=unit_id)

        if not unit.is_available:
            return Response({"error": "Unit is not available"}, status=status.HTTP_400_BAD_REQUEST)

        tenant = request.user
        amount = unit.deposit
        phone_number = tenant.phone_number

        if not phone_number:
            return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate phone number format
        if not phone_number.startswith('254'):
            return Response({"error": "Phone number must be in format 254XXXXXXXXX"}, status=status.HTTP_400_BAD_REQUEST)
        # ✅ ADD VALIDATION HERE
        is_valid, validation_message = validate_mpesa_payment(phone_number, amount)
        if not is_valid:
            return Response({"error": validation_message}, status=status.HTTP_400_BAD_REQUEST)
        # Generate access token
        access_token = generate_access_token()
        if not access_token:
            return Response({"error": "Failed to generate M-Pesa access token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare STK push request for PRODUCTION
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode('utf-8')
        ).decode('utf-8')

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_DEPOSIT_CALLBACK_URL,
            "AccountReference": f"DEPOSIT-{unit.unit_code}",
            "TransactionDesc": f"Deposit payment for {unit.unit_number}"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Use production URL
        if settings.MPESA_ENV == "sandbox":
            url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        else:
            url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ResponseCode") == "0":
            # Create pending deposit payment record
            payment = Payment.objects.create(
                tenant=tenant,
                unit=unit,
                amount=amount,
                status="Pending",
                payment_type="deposit",
                mpesa_checkout_request_id=response_data["CheckoutRequestID"]
            )

            # Cache checkout request ID for callback
            cache.set(f"stk_deposit_{response_data['CheckoutRequestID']}", {
                "payment_id": payment.id,
                "unit_id": unit.id,
                "amount": float(amount),
                "tenant_id": tenant.id
            }, timeout=300)  # 5 minutes

            logger.info(f"Deposit STK push initiated for payment {payment.id}, amount {amount}")

            return Response({
                "success": True,
                "message": "Deposit STK push initiated successfully",
                "checkout_request_id": response_data["CheckoutRequestID"],
                "payment_id": payment.id
            })

        else:
            logger.error(f"Deposit STK push failed: {response_data}")
            return Response({
                "error": "Failed to initiate deposit STK push",
                "details": response_data.get('errorMessage', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)


class DepositPaymentStatusView(APIView):
    """
    Check deposit payment status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)

        # Check if user has permission to view this payment
        if request.user.user_type == 'tenant' and payment.tenant != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if request.user.user_type == 'landlord' and payment.unit.property_obj.landlord != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "payment_id": payment.id,
            "status": payment.status,
            "amount": payment.amount,
            "mpesa_receipt": payment.mpesa_receipt
        })


class CleanupPendingPaymentsView(APIView):
    """
    Clean up old pending payments
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete pending payments older than 1 hour
        cutoff_time = timezone.now() - timedelta(hours=1)
        deleted_count = Payment.objects.filter(
            status='Pending',
            transaction_date__lt=cutoff_time
        ).delete()

        return Response({"message": f"Cleaned up {deleted_count[0]} pending payments"})


# ------------------------------
# CSV EXPORT VIEWS
# ------------------------------

class LandLordCSVView(APIView):
    """
    Export landlord payment data as CSV
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, property_id):
        user = request.user
        if user.user_type != 'landlord':
            return Response({"error": "Only landlords can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)

        property_obj = get_object_or_404(Property, id=property_id, landlord=user)
        units = Unit.objects.filter(property_obj=property_obj)
        payments = Payment.objects.filter(unit__in=units, status='Success')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="landlord_payments_{property_obj.name}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Unit Number', 'Tenant', 'Amount', 'Date', 'M-Pesa Receipt'])

        for payment in payments:
            writer.writerow([
                payment.unit.unit_number,
                payment.tenant.full_name if payment.tenant else '',
                payment.amount,
                payment.transaction_date.strftime('%Y-%m-%d'),
                payment.mpesa_receipt or ''
            ])

        return response


class TenantCSVView(APIView):
    """
    Export tenant payment data as CSV
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        user = request.user
        unit = get_object_or_404(Unit, id=unit_id)

        if user.user_type == 'tenant' and unit.tenant != user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if user.user_type == 'landlord' and unit.property_obj.landlord != user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        payments = Payment.objects.filter(unit=unit, status='Success')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="tenant_payments_unit_{unit.unit_number}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Amount', 'Date', 'M-Pesa Receipt', 'Type'])

        for payment in payments:
            writer.writerow([
                payment.amount,
                payment.transaction_date.strftime('%Y-%m-%d'),
                payment.mpesa_receipt or '',
                payment.payment_type
            ])

        return response


class TestMpesaView(APIView):
    """
    Test endpoint for M-Pesa integration
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "M-Pesa test endpoint",
            "mpesa_env": settings.MPESA_ENV,
            "shortcode": settings.MPESA_SHORTCODE
        })

    def post(self, request):
        # Test token generation
        token = generate_access_token()
        if token:
            return Response({
                "success": True,
                "message": "M-Pesa token generated successfully",
                "token_preview": token[:10] + "..."
            })
        else:
            return Response({
                "success": False,
                "message": "Failed to generate M-Pesa token"
            }, status=400)
