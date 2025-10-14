# TODO List

## STK Push Payment Callback and Tenant Assignment Fix

### Completed Tasks
- [x] Remove polling logic from AssignTenantToUnitView in accounts/views.py
- [x] Update view to return success immediately after payment initiation
- [x] Ensure mpesa_deposit_callback handles tenant assignment upon successful payment

### Pending Tasks
- [x] Add more detailed logging to callback for debugging payment flow
- [ ] Test the callback functionality to ensure it waits for actual payment completion
- [ ] Verify callback URL configuration in settings
- [ ] Test end-to-end payment flow with real M-Pesa simulation

### Notes
- Tenant assignment now handled solely by callback to avoid race conditions
- View initiates payment and informs user that assignment occurs upon successful payment
- Callback includes fallback logic for payment matching
