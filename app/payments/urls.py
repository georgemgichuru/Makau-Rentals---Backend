from django.urls import path
from .views import (
    # STK Push + Callbacks
    stk_push,
    mpesa_rent_callback,
    mpesa_subscription_callback,

    # DRF views
    PaymentListCreateView,
    PaymentDetailView,
    SubscriptionPaymentListCreateView,
    SubscriptionPaymentDetailView,
    RentSummaryView,
)

urlpatterns = [
    # ------------------------------
    # M-PESA STK PUSH + CALLBACKS
    # ------------------------------
    path("stk-push/<int:unit_id>/", stk_push, name="stk-push"),
    path("callback/rent/", mpesa_rent_callback, name="mpesa-rent-callback"),
    path("callback/subscription/", mpesa_subscription_callback, name="mpesa-subscription-callback"),

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
]
