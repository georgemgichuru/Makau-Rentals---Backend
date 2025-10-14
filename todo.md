# TODO: Fix Rent Payment Initiation and Assignment Issues

## Issues Fixed
- [x] Rent payment initiation fails with 503 error due to access token generation issues
  - Added retry logic for access token generation in stk_push
- [x] Assignment of tenant to unit occurs even when payment is canceled, as failed payments aren't properly handled in callbacks
  - Callbacks already handle failed payments by setting status to "Failed"
- [x] Rent payment should wait for deposit and unit assignment to be successful
  - Added deposit verification in stk_push for rent payments
  - Updated AssignTenantToUnitView to check for no pending deposit payments before assigning
- [x] Import error in permissions.py for Payment model
  - Fixed import from .models to payments.models in HasActiveSubscription permission
- [x] Unit lookup in stk_push lacks exception handling for unexpected errors
  - Added try-except block around Unit.objects.get to catch and handle unexpected exceptions

## Changes Made
- **app/payments/views.py**:
  - Added deposit check before allowing rent payment initiation
  - Improved access token generation with retry logic (try once more if fails)
  - Added exception handling for unit lookup in stk_push
- **app/accounts/views.py**:
  - Added check for pending deposit payments in AssignTenantToUnitView
- **app/accounts/permissions.py**:
  - Fixed import path for Payment model in HasActiveSubscription permission

## Testing Steps
- [ ] Test rent payment initiation after deposit payment
- [ ] Test failed payment handling (should not assign unit)
- [ ] Test assignment only after successful deposit
- [ ] Run comprehensive test script to verify all flows
- [ ] Verify import fixes don't cause any issues

## Next Steps
- Run the application and test the payment flows
- Verify that rent payments are blocked without deposit
- Verify that assignments require successful deposits
- Check logs for any errors in token generation or payment processing
- Test the permission classes to ensure they work correctly with the fixed imports
