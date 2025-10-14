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
    TriggerDepositCallbackView,

    # CSV reports
    LandLordCSVView as landlord_csv,
    TenantCSVView as tenant_csv,
)
from django.views.decorators.csrf import csrf_exempt

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
    path("trigger-deposit-callback/", TriggerDepositCallbackView.as_view(), name="trigger-deposit-callback"),

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
