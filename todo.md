# TODO: Add Delay to STK Push Payments

## Steps to Complete

- [x] Import `time` module at the top of `app/payments/views.py`
- [x] Modify `stk_push` function (rent payment):
  - After successful API call, add a loop to wait up to 30 seconds
  - Check payment status every second
  - If status becomes 'Success', return success message with receipt
  - If timeout, set status to 'Failed' and return error message
- [x] Modify `stk_push_subscription` function:
  - After successful API call, add a loop to wait up to 30 seconds
  - Check subscription payment status every second
  - If status becomes 'Success', return success message with receipt
  - If timeout, set status to 'Failed' and return error message
- [x] Modify `InitiateDepositPaymentView.post` method:
  - After successful API call, add a loop to wait up to 30 seconds
  - Check payment status every second
  - If status becomes 'Success', return success message with receipt
  - If timeout, set status to 'Failed' and return error message
- [x] Test the changes to ensure payments work correctly with the delay

## Fix 403 Forbidden on Tenant Rent Payments List

- [x] Add HasActiveSubscription to PaymentListCreateView permission_classes to match PaymentDetailView
- [x] This ensures tenants can only access their payments if the landlord's subscription is active
- [x] Landlord has free plan which is active, so test should pass
