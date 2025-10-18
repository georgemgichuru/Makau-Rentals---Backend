# TODO: Update test.ps1 for InitiateDepositPaymentView Changes

## Steps to Complete
- [x] Modify the deposit payment initiation section in test.ps1 to call the simulate deposit callback endpoint after initiating the payment.
- [x] Remove the polling function (Invoke-PollDepositPaymentStatus) and replace it with a single call to check payment status after simulation.
- [x] Update the script to use the correct endpoint for simulation: POST to /api/payments/simulate-deposit-callback/ with payment_id in the body.
- [x] Test the updated script to ensure deposit payment is simulated successfully and status is checked correctly.
