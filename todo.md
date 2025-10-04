# TODO: Implement Subscription-Based Access and Payment Flow

## 1. Improve Subscription Enforcement
- [x] Update `app/accounts/permissions.py` to add a permission class or decorator that checks if a tenant's landlord has an active subscription.
- [ ] Apply subscription checks to tenant-facing views in payments app.

## 2. Verify Payment Till Numbers
- [x] Confirm in `app/payments/views.py` that subscription payments use the hardcoded central shortcode (user's till).
- [x] Confirm rent payments use landlord's mpesa_till_number if set, else central shortcode.

## 3. Add Landlord Till Number Update Endpoint
- [x] Add a new view in `app/accounts/views.py` for landlords to update their mpesa_till_number.
- [x] Add serializer for updating till number in `app/accounts/serializers.py`.
- [x] Add URL pattern in `app/accounts/urls.py`.

## 4. Enforce Subscription in Views
- [ ] Apply subscription permission to tenant views like stk_push for rent payments.
- [ ] Ensure landlords can only access their own data if subscribed.

## 5. Testing
- [ ] Test subscription payment flow to user's till.
- [ ] Test rent payment flow to landlord's till.
- [ ] Test access restrictions for unsubscribed users.
- [ ] Test till number update for landlords.
