# M-Pesa Daraja Setup and Fixes

## Tasks
- [x] Fix import error in app/payments/views.py: Remove Unit from from .models import
- [x] Remove subscription update logic from SubscriptionPayment model save method
- [x] In mpesa_subscription_callback, convert amount to int for plan matching
- [x] Ensure onetime plan sets expiry_date = None in subscription updates
- [x] Remove duplicate unit balance update in mpesa_rent_callback
- [x] Verify callback URLs in settings

## Followup
- [ ] Run migrations if needed
- [ ] Set env vars for M-Pesa
- [ ] Test payments
