# TODO: Update Payments Code

## Tasks
- [ ] Update SubscriptionPayment model in models.py to allow empty mpesa_receipt_number with conditional uniqueness
- [ ] Add logger to CleanupPendingPaymentsView post method in views.py
- [ ] Update RentSummaryView permissions to remove HasActiveSubscription
- [ ] Verify stk_push_subscription function matches provided code
- [ ] Run migrations for model changes
- [ ] Test the updated endpoints
