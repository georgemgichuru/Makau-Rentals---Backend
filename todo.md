# TODO: Fix Deposit Payment Callback Registration

## Information Gathered
- Deposit STK push initiation succeeds and creates a pending Payment record with payment_type='deposit'.
- The callback (mpesa_deposit_callback) should update the Payment status to 'Success' upon receiving M-Pesa confirmation.
- Tenant assignment to unit requires a successful deposit payment.
- In the test script, deposit initiation fails with 500 (expected without M-Pesa setup), so no payment is created, leading to assignment failure.
- In production, STK push succeeds, but the callback may not be reaching the server or processing correctly due to misconfigured callback URL or server issues.

## Plan
1. **Verify Callback URL Configuration**: Ensure MPESA_DEPOSIT_CALLBACK_URL is correctly set in settings.py (defaults to MPESA_CALLBACK_URL).
2. **Add Detailed Logging to Callback**: Enhance mpesa_deposit_callback with logging at entry, success, and failure points to debug callback reception and processing.
3. **Fix Amount Conversion**: Convert amount to float in callback, similar to rent callback.
4. **Test Callback Simulation**: Update the test script to properly simulate the deposit callback and verify payment status update.
5. **Add Manual Callback Trigger**: Create a test endpoint to manually trigger callback for debugging.

## Dependent Files to be Edited
- `app/app/settings.py`: Verify MPESA_DEPOSIT_CALLBACK_URL.
- `app/payments/views.py`: Add logging and fix amount conversion in mpesa_deposit_callback.
- `app/comprehensive_test_v2.ps1`: Update callback simulation to handle deposit payments correctly.

## Followup Steps
- Deploy changes and test deposit payment flow in production.
- Monitor logs for callback reception.
- If issues persist, check server logs and M-Pesa dashboard for callback delivery.
