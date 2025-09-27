import base64
import datetime
import requests
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Unit, Payment
from .generate_token import generate_access_token
from django.views.decorators.csrf import csrf_exempt


@login_required
def stk_push(request, unit_id):
    try:
        # Get tenant's unit
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

        # Build payload
        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(payment.amount),  # Rent due
            "PartyA": request.user.phone_number,  # Tenant phone number (must be in 2547XXXXXXX format)
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": request.user.phone_number,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
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


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Payment, Unit

@csrf_exempt
def mpesa_callback(request):
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
            account_ref = body.get("MerchantRequestID") or body.get("CheckoutRequestID")

            # If you passed payment.id as AccountReference in stk_push:
            payment_id = body.get("AccountReference") or None

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
            # You can log or update the Payment as failed
            print("Transaction failed:", body)

    except Exception as e:
        print("Error processing callback:", e)

    # Always respond with success to Safaricom, even if you had internal errors
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


