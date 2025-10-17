# Payment System Fixes

## Critical Issues
- [ ] Fix deposit payment initiation (allow payments for vacant units)
- [ ] Improve phone number normalization for Kenyan numbers
- [ ] Allow decimal amounts for deposits
- [ ] Fix callback metadata parsing and error handling
- [ ] Improve user lookup in subscription callbacks
- [ ] Fix authentication issues causing unauthorized errors
- [ ] Enhance M-Pesa API error handling and logging

## Testing
- [ ] Test deposit payment initiation
- [ ] Test rent payment initiation
- [ ] Test subscription payment initiation
- [ ] Test callback processing with mock data
- [ ] Verify authentication works properly

## Files Modified
- app/payments/views.py
- app/payments/generate_token.py
- app/app/settings.py
