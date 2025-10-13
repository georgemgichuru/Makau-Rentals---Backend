# TODO: Replace M-Pesa Express with B2C for Rent Payments

## Overview
Replace the current STK Push to landlord's till with a centralized flow: Tenant pays to app's shortcode via STK Push, then app disburses to landlord via B2C. This removes the need for landlords to provide till numbers.

## Tasks
- [ ] Modify `stk_push` function to always use central shortcode for rent payments
- [ ] Add B2C disbursement function in `generate_token.py`
- [ ] Update `mpesa_rent_callback` to initiate B2C after successful payment
- [ ] Modify `InitiateDepositPaymentView` to use central shortcode
- [ ] Update `mpesa_deposit_callback` to initiate B2C for deposits
- [ ] Test the new payment flow
- [ ] Update documentation if needed

## Notes
- Ensure landlord has phone_number set for B2C disbursements
- B2C requires additional API credentials (if not already present)
- Remove dependency on `unit.property_obj.landlord.mpesa_till_number` for rent/deposit
