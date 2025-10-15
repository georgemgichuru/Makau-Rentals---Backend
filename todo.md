# TODO: Update Makau Rentals Payment Features

## Pending Tasks
- [ ] Update DepositPaymentStatusView in app/payments/views.py to include timeout detection (10 minutes)
- [ ] Add CleanupPendingPaymentsView after DepositPaymentStatusView in app/payments/views.py
- [ ] Add SimulateDepositCallbackView after CleanupPendingPaymentsView in app/payments/views.py
- [ ] Add URL patterns for cleanup and simulation endpoints in app/payments/urls.py
- [ ] Update comprehensive_test_v2.ps1 with testing logic for new cleanup and simulation endpoints
- [ ] Test the updated functionality
