# TODO: Implement B2C for Rent Payments

## Tasks
- [ ] Modify `mpesa_rent_callback` to initiate B2C payment to landlord after successful payment update
- [ ] Use landlord's `mpesa_till_number` if available, else `phone_number`
- [ ] Create B2C callback view (`mpesa_b2c_callback`) to handle disbursement confirmations
- [ ] Update `app/payments/urls.py` to include B2C callback URL
- [ ] Ensure B2C settings are present in `app/app/settings.py`
- [ ] Update `initiate_b2c_payment` to handle till numbers if needed
- [ ] Test the flow

## Notes
- B2C can use phone number or till number as PartyB
- Handle B2C failures gracefully
- Ensure money goes directly to landlord
