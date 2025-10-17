# TODO: Enhance test.ps1 for Real M-Pesa Transactions

## Steps to Complete
- [ ] Update phone number variables to prompt user for real phone numbers using Read-Host
- [ ] Modify rent payment section: Remove callback simulation, add polling for payment status after STK push initiation
- [ ] Modify subscription payment section: Remove callback simulation, add polling for payment status after STK push initiation
- [ ] Ensure deposit payment polling is retained and handles real transactions
- [ ] Add post-payment checks: List rent payments, subscription payments, and rent summary after real transactions
- [ ] Improve error handling for payment failures (e.g., user cancellation) with appropriate messages
- [ ] Test the script to ensure real STK pushes are triggered and statuses are polled correctly
- [ ] Verify minimal amounts (10 KSH deposit, 100 KSH rent, 50 KSH subscription) are used to avoid high costs
