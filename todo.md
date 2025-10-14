# TODO: Fix Tenant Assignment Logic for Deposit Payments

## Completed Tasks
- [x] Modify deposit callback to check 30-second timeout
- [x] Ensure tenant assignment only on successful payments within 30 seconds
- [x] Mark cancelled payments (ResultCode != 0) as Failed without assignment
- [x] Add logging for timeout scenarios

## Pending Tasks
- [ ] Implement periodic cleanup task for old pending payments (requires Celery fix)
- [ ] Test the timeout logic with manual callback triggering
- [ ] Verify cache invalidation works correctly for failed payments

## Notes
- Celery is currently broken, so periodic cleanup cannot be implemented yet
- All changes are in `app/payments/views.py` in the `mpesa_deposit_callback` function
- The system now prevents "fake" payments by enforcing the 30-second window
