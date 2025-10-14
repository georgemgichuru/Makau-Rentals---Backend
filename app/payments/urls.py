from django.urls import path
from .views import (
    # STK Push + Callbacks
    stk_push,
    stk_push_subscription,
    mpesa_rent_callback,
    mpesa_subscription_callback,
    mpesa_b2c_callback,
    mpesa_deposit_callback,

    # DRF views
    PaymentListCreateView,
    PaymentDetailView,
    SubscriptionPaymentListCreateView,
    SubscriptionPaymentDetailView,
    RentSummaryView,
    UnitTypeListView,
    InitiateDepositPaymentView,

    # CSV reports
    LandLordCSVView as landlord_csv,
    TenantCSVView as tenant_csv,
)
from django.views.decorators.csrf import csrf_exempt
# ------------------------------
# MANUAL CALLBACK TRIGGER FOR TESTING
# ------------------------------
@csrf_exempt
def trigger_deposit_callback(request):
    """
    Manual endpoint to trigger deposit callback for testing.
    Accepts payment_id as query parameter.
    """
    from django.http import JsonResponse
    from .models import Payment
    import json
    import logging

    logger = logging.getLogger(__name__)

    if request.method != 'POST':
        return JsonResponse({"error": "POST method required"}, status=405)

    payment_id = request.GET.get('payment_id')
    if not payment_id:
        return JsonResponse({"error": "payment_id query parameter required"}, status=400)

    try:
        payment = Payment.objects.get(id=payment_id, payment_type='deposit')
    except Payment.DoesNotExist:
        return JsonResponse({"error": f"Deposit payment with id {payment_id} not found"}, status=404)

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
    from django.http import HttpRequest
    mock_request = HttpRequest()
    mock_request.method = 'POST'
    mock_request._body = json.dumps(mock_callback_data).encode('utf-8')

    logger.info(f"🔧 Manually triggering deposit callback for payment {payment_id}")
    response = mpesa_deposit_callback(mock_request)

    return JsonResponse({
        "message": f"Deposit callback triggered for payment {payment_id}",
        "mock_data": mock_callback_data,
        "callback_response": response.content.decode('utf-8')
    })

urlpatterns = [
    # ------------------------------
    # M-PESA STK PUSH + CALLBACKS
    # ------------------------------
    path("stk-push/<int:unit_id>/", stk_push, name="stk-push"),
    path("stk-push-subscription/", stk_push_subscription, name="stk-push-subscription"),
    path("callback/rent/", mpesa_rent_callback, name="mpesa-rent-callback"),
    path("callback/subscription/", mpesa_subscription_callback, name="mpesa-subscription-callback"),
    path("callback/b2c/", mpesa_b2c_callback, name="mpesa-b2c-callback"),
    path("callback/deposit/", mpesa_deposit_callback, name="mpesa-deposit-callback"),

    # ------------------------------
    # MANUAL CALLBACK TRIGGER (FOR TESTING)
    # ------------------------------
    path("trigger-deposit-callback/", trigger_deposit_callback, name="trigger-deposit-callback"),

    # ------------------------------
    # RENT PAYMENTS (DRF)
    # ------------------------------
    path("rent-payments/", PaymentListCreateView.as_view(), name="rent-payment-list-create"),
    path("rent-payments/<int:pk>/", PaymentDetailView.as_view(), name="rent-payment-detail"),

    # ------------------------------
    # SUBSCRIPTION PAYMENTS (DRF)
    # ------------------------------
    path("subscription-payments/", SubscriptionPaymentListCreateView.as_view(), name="subscription-payment-list-create"),
    path("subscription-payments/<int:pk>/", SubscriptionPaymentDetailView.as_view(), name="subscription-payment-detail"),
    path("rent-payments/summary/", RentSummaryView.as_view(), name="rent-summary"),

    # ------------------------------
    # UNIT TYPES
    # ------------------------------
    path("unit-types/", UnitTypeListView.as_view(), name="unit-types"),

    # ------------------------------
    # INITIATE DEPOSIT PAYMENT
    # ------------------------------
    path("initiate-deposit/", InitiateDepositPaymentView.as_view(), name="initiate-deposit"),

    # ------------------------------
    # CSV REPORTS
    # ------------------------------
    path("landlord-csv/<int:property_id>/", landlord_csv.as_view(), name="landlord-csv"),
    path("tenant-csv/<int:unit_id>/", tenant_csv.as_view(), name="tenant-csv"),
]
