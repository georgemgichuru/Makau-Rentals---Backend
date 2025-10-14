# TODO: Fix Rent Payment Initiation and Assignment Issues

## Issues Fixed
- [x] Rent payment initiation fails with 503 error due to access token generation issues
  - Added retry logic for access token generation in stk_push
- [x] Assignment of tenant to unit occurs even when payment is canceled, as failed payments aren't properly handled in callbacks
  - Callbacks already handle failed payments by setting status to "Failed"
- [x] Rent payment should wait for deposit and unit assignment to be successful
  - Added deposit verification in stk_push for rent payments
  - Updated AssignTenantToUnitView to check for no pending deposit payments before assigning

## Changes Made
- **app/payments/views.py**:
  - Added deposit check before allowing rent payment initiation
  - Improved access token generation with retry logic (try once more if fails)
- **app/accounts/views.py**:
  - Added check for pending deposit payments in AssignTenantToUnitView

## Testing Steps
- [ ] Test rent payment initiation after deposit payment
- [ ] Test failed payment handling (should not assign unit)
- [ ] Test assignment only after successful deposit
- [ ] Run comprehensive test script to verify all flows

## Next Steps
- Run the application and test the payment flows
- Verify that rent payments are blocked without deposit
- Verify that assignments require successful deposits
- Check logs for any errors in token generation or payment processing
