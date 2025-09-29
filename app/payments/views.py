import base64
import datetime
import json
import requests
import csv
from django.http import HttpResponse
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from accounts.models import CustomUser, Subscription, Property, Unit
from .models import Unit, Payment, SubscriptionPayment
from .generate_token import generate_access_token

from rest_framework import generics, permissions
from .serializers import PaymentSerializer, SubscriptionPaymentSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


# ------------------------------
# STK PUSH INITIATION (Tenant Rent Payment)
# ------------------------------
@login_required
def stk_push(request, unit_id):
    """
    Initiates an M-Pesa STK Push for a tenant's rent payment.
    - Creates a pending Payment record
    - Calls Safaricom STK Push API
    """
    try:
        # Ensure the unit belongs to the logged-in tenant
        unit = Unit.objects.get(id=unit_id, tenant=request.user)

        # Create a pending payment record
        payment = Payment.objects.create(
            tenant=request.user,
            unit=unit,
            amount=unit.rent_remaining,
            status="Pending"
        )

        # Generate access token
        access_token = generate_access_token()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")

        # Build payload for Safaricom API
        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(payment.amount),  # Rent due
            "PartyA": request.user.phone_number,  # Tenant phone number (must be in 2547XXXXXXX format)
            "PartyB": settings.MPESA_SHORTCODE,
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

        return JsonResponse(response.json())

    except Unit.DoesNotExist:
        return JsonResponse({"error": "Unit not found or not assigned to you"}, status=404)


# ------------------------------
# RENT PAYMENT CALLBACK
# ------------------------------
@csrf_exempt
def mpesa_rent_callback(request):
    """
    Handles M-Pesa callback for rent payments.
    - Updates Payment status
    - Updates Unit rent balances
    """
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
                    payment = Payment.objects.get(id=payment_id, status="Pending")
                    payment.status = "Success"
                    payment.mpesa_receipt = receipt
                    payment.save()

                    # Update unit balances
                    unit = payment.unit
                    unit.rent_paid += amount
                    unit.rent_remaining = max(unit.rent - unit.rent_paid, 0)
                    unit.save()

                except Payment.DoesNotExist:
                    print(f"Payment with id {payment_id} not found or already processed")

        else:
            # ❌ Transaction failed
            print("Transaction failed:", body)

    except Exception as e:
        print("Error processing rent callback:", e)

    # Always respond with success to Safaricom
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# ------------------------------
# SUBSCRIPTION PAYMENT CALLBACK
# ------------------------------
@csrf_exempt
def mpesa_subscription_callback(request):
    """
    Handles M-Pesa callback for subscription payments.
    - Creates SubscriptionPayment record
    - Updates landlord's Subscription plan and expiry
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")

        if result_code == 0:  # ✅ Transaction successful
            metadata_items = body.get("CallbackMetadata", {}).get("Item", [])
            metadata = {item["Name"]: item.get("Value") for item in metadata_items}

            amount = metadata.get("Amount")
            receipt = metadata.get("MpesaReceiptNumber")
            phone = str(metadata.get("PhoneNumber"))

            # Find landlord by phone number
            user = CustomUser.objects.filter(user_type='landlord', phone_number=phone).first()
            if not user:
                return JsonResponse({'error': 'Landlord not found'}, status=404)

            # Map amount to subscription type and duration
            plans = {
                500: ("basic", timedelta(days=30)),
                1000: ("premium", timedelta(days=60)),
                2000: ("enterprise", timedelta(days=90)),
            }
            if amount not in plans:
                return JsonResponse({'error': 'Invalid amount'}, status=400)

            sub_type, duration = plans[amount]

            # Save subscription payment
            SubscriptionPayment.objects.create(
                user=user,
                amount=amount,
                mpesa_receipt_number=receipt,
                subscription_type=sub_type
            )

            # Update or create subscription
            subscription, _ = Subscription.objects.get_or_create(user=user)
            subscription.plan = sub_type
            subscription.start_date = timezone.now()
            subscription.expiry_date = timezone.now() + duration
            subscription.save()

        else:
            print("Subscription transaction failed:", body)

    except Exception as e:
        print("Error processing subscription callback:", e)

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# ------------------------------
# RENT PAYMENTS (DRF Views)
# ------------------------------
class PaymentListCreateView(generics.ListCreateAPIView):
    """
    GET: List all rent payments (can be filtered by tenant or unit).
    POST: Create a new rent payment for a tenant.
    """
    queryset = Payment.objects.all().order_by('-transaction_date')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Automatically associate the logged-in user if they are a tenant.
        """
        if self.request.user.user_type == "tenant":
            serializer.save(tenant=self.request.user)
        else:
            serializer.save()


class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve details of a single rent payment by ID.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]


# ------------------------------
# SUBSCRIPTION PAYMENTS (DRF Views)
# ------------------------------
class SubscriptionPaymentListCreateView(generics.ListCreateAPIView):
    """
    GET: List all subscription payments (landlords only).
    POST: Create a new subscription payment for a landlord.
    """
    queryset = SubscriptionPayment.objects.all().order_by('-transaction_date')
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Automatically associate the logged-in landlord with the subscription payment.
        """
        if self.request.user.user_type == "landlord":
            serializer.save(user=self.request.user)
        else:
            raise PermissionError("Only landlords can make subscription payments.")


class SubscriptionPaymentDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve details of a single subscription payment by ID.
    """
    queryset = SubscriptionPayment.objects.all()
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]


# ------------------------------
# RENT PAYMENTS (DRF Views)
# ------------------------------
class PaymentListCreateView(generics.ListCreateAPIView):
    """
    GET:
      - Tenants: only see their own rent payments.
      - Landlords: see all rent payments for units in their properties.
    POST:
      - Only tenants can create a new rent payment.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "tenant":
            # Tenant only sees their own payments
            return Payment.objects.filter(tenant=user).order_by('-transaction_date')
        elif user.user_type == "landlord":
            # Landlord sees all payments for units in properties they own
            return Payment.objects.filter(unit__property__landlord=user).order_by('-transaction_date')
        return Payment.objects.none()

    def perform_create(self, serializer):
        if self.request.user.user_type == "tenant":
            serializer.save(tenant=self.request.user)
        else:
            raise PermissionError("Only tenants can create rent payments.")


class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET:
      - Tenants: can only view their own payment details.
      - Landlords: can view payment details for units in their properties.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "tenant":
            return Payment.objects.filter(tenant=user)
        elif user.user_type == "landlord":
            return Payment.objects.filter(unit__property__landlord=user)
        return Payment.objects.none()


# ------------------------------
# SUBSCRIPTION PAYMENTS (DRF Views)
# ------------------------------
class SubscriptionPaymentListCreateView(generics.ListCreateAPIView):
    """
    GET:
      - Landlords: only see their own subscription payments.
      - Tenants: no access.
    POST:
      - Only landlords can create subscription payments.
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "landlord":
            return SubscriptionPayment.objects.filter(user=user).order_by('-transaction_date')
        return SubscriptionPayment.objects.none()

    def perform_create(self, serializer):
        if self.request.user.user_type == "landlord":
            serializer.save(user=self.request.user)
        else:
            raise PermissionError("Only landlords can make subscription payments.")


class SubscriptionPaymentDetailView(generics.RetrieveAPIView):
    """
    GET:
      - Landlords: can only view their own subscription payment details.
    """
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "landlord":
            return SubscriptionPayment.objects.filter(user=user)
        return SubscriptionPayment.objects.none()


class RentSummaryView(APIView):
    """
    Provides a financial summary for landlords:
      - Total rent collected across all their properties
      - Total outstanding rent
      - Per-unit breakdown (unit number, tenant, paid, remaining)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.user_type != "landlord":
            return Response({"error": "Only landlords can view rent summaries."}, status=403)

        # Get all units owned by this landlord
        units = Unit.objects.filter(property__landlord=user)

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
        }

        return Response(summary)


# ------------------------------
# GENERATE RENT PAYMENTS CSV REPORT
# ------------------------------
# for landlord to download CSV of all units and their rent status
from django.shortcuts import get_object_or_404

def landlord_csv(request, property_id):
    property = get_object_or_404(Property, pk=property_id)
    units = property.unit_list.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="landlord_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['tenant','Unit Number', 'Floor', 'Bedrooms', 'Bathrooms', 'Rent', 'Rent Paid', 'Rent Remaining', 'Rent Due Date', 'Deposit', 'Is Available'])
    for unit in units:
        writer.writerow([unit.tenant,unit.unit_number, unit.floor, unit.bedrooms, unit.bathrooms, unit.rent, unit.rent_paid, unit.balance, unit.rent_due_date, unit.deposit, unit.is_available])

    return response

# for tenants to download CSV of their rent payment history
def tenant_csv(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tenant_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['Unit Number', 'Floor', 'Bedrooms', 'Bathrooms', 'Rent', 'Rent Paid', 'Rent Remaining', 'Rent Due Date', 'Deposit'])
    writer.writerow([unit.property_obj.name, unit.unit_number, unit.floor, unit.bedrooms, unit.bathrooms, unit.rent, unit.rent_paid, unit.balance, unit.rent_due_date, unit.deposit])
    return response

