# TODO: Fix Rent Payment Initiation and Assignment Issues

## Issues to Fix
1. Rent payment initiation fails with 503 error due to access token generation issues.
2. Assignment of tenant to unit occurs even when payment is canceled, as failed payments aren't properly handled in callbacks.
3. Rent payment should wait for deposit and unit assignment to be successful.

## Steps
- [ ] Update mpesa_rent_callback to handle failed payments (set status to "Failed" if ResultCode != 0)
- [ ] Update mpesa_deposit_callback to handle failed payments (set status to "Failed" if ResultCode != 0)
- [ ] Improve error handling in stk_push (rent payment) to retry access token generation once before failing
- [ ] Modify AssignTenantToUnitView to check for no pending payments before assigning tenant to unit
- [ ] Add deposit verification for rent payments in stk_push function
- [ ] Update tenant signup to not assign units unless deposit is confirmed
- [ ] Test the fixes using the comprehensive test script
