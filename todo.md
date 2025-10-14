# Task: Modify AssignTenantToUnitView to Initiate Deposit Payment and Wait for Confirmation

## Completed Tasks
- [x] Modified AssignTenantToUnitView in app/accounts/views.py
  - Removed check for existing successful deposit payment
  - Added STK push initiation for deposit payment
  - Implemented polling logic to wait up to 30 seconds for payment confirmation
  - Assign tenant only when payment status becomes 'Success'
  - Return appropriate error messages for failed payments or timeouts
  - Added rate limiting and duplicate payment prevention
  - Invalidated relevant caches on success

## Followup Steps
- [ ] Test the endpoint to ensure payment initiation and assignment work correctly
- [ ] Verify callback handling updates payment status properly
- [ ] Check error handling for various scenarios (payment failure, timeout, etc.)
