# Migration and M-Pesa Integration Fixes

## 1. Migration Reset
- [ ] Delete all migration files except __init__.py in all apps
- [ ] Run makemigrations
- [ ] Run migrate

## 2. Update Requirements
- [ ] Add missing dependencies: celery>=5.0.0, redis>=4.0.0, django-cors-headers>=4.0.0, python-decouple>=3.0.0

## 3. Fix M-Pesa Token Generation
- [ ] Update payments/generate_token.py with improved error handling

## 4. Fix STK Push Function
- [ ] Update stk_push in payments/views.py with better error handling and validation

## 5. Fix SubscriptionPayment Model
- [ ] Update payments/models.py to use simple unique constraint

## 6. Update Settings
- [ ] Change CACHES to DummyCache for Render deployment
- [ ] Ensure M-Pesa environment variables are configured

## 7. Add Test M-Pesa View
- [ ] Add TestMpesaView to payments/views.py
- [ ] Add URL pattern for test-mpesa

## 8. Environment Variables
- [ ] Document required MPESA_* environment variables for Render

## 9. Testing
- [ ] Test M-Pesa integration after deployment
