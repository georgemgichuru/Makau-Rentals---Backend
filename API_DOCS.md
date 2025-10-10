# Makau Rentals API Documentation

This document provides a comprehensive overview of the API endpoints for the Makau Rentals application. The API is built with Django REST Framework and uses JWT for authentication.

## Base URL
The base URL for all endpoints is `http://localhost:8000/api/` (assuming the server is running on port 8000).

## Authentication
Most endpoints require authentication. Use JWT tokens obtained from the login endpoint.

### Obtain Token
- **Endpoint**: `POST /accounts/token/`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "password"
  }
  ```
- **Response**:
  ```json
  {
    "refresh": "refresh_token",
    "access": "access_token"
  }
  ```

### Refresh Token
- **Endpoint**: `POST /accounts/token/refresh/`
- **Body**:
  ```json
  {
    "refresh": "refresh_token"
  }
  ```

## Accounts App Endpoints

### User Management

#### Signup
- **Endpoint**: `POST /accounts/signup/`
- **Description**: Create a new user (landlord or tenant).
- **Permissions**: None
- **Body** (example for landlord):
  ```json
  {
    "email": "landlord@example.com",
    "password": "password",
    "full_name": "John Doe",
    "user_type": "landlord",
    "phone_number": "+254712345678",
    "properties": [
      {
        "name": "Property 1",
        "city": "Nairobi",
        "state": "Kenya",
        "unit_count": 10,
        "vacant_units": 5
      }
    ]
  }
  ```

#### Get User Details
- **Endpoint**: `GET /accounts/users/{user_id}/`
- **Permissions**: Authenticated

#### List Users (Landlords only)
- **Endpoint**: `GET /accounts/users/`
- **Permissions**: Landlord

#### Update User
- **Endpoint**: `PUT /accounts/users/{user_id}/update/`
- **Permissions**: Authenticated (own user)

#### Delete User
- **Endpoint**: `DELETE /accounts/users/{user_id}/update/`
- **Permissions**: Authenticated (own user)

#### Get Current User
- **Endpoint**: `GET /accounts/me/`
- **Permissions**: Authenticated

#### Update Current User
- **Endpoint**: `PUT /accounts/me/`
- **Permissions**: Authenticated

### Property Management

#### Create Property
- **Endpoint**: `POST /accounts/properties/create/`
- **Permissions**: Landlord with active subscription
- **Body**:
  ```json
  {
    "name": "Property Name",
    "city": "City",
    "state": "State"
  }
  ```

#### List Properties
- **Endpoint**: `GET /accounts/properties/`
- **Permissions**: Landlord

#### Update Property
- **Endpoint**: `PUT /accounts/properties/{property_id}/update/`
- **Permissions**: Landlord

#### Delete Property
- **Endpoint**: `DELETE /accounts/properties/{property_id}/update/`
- **Permissions**: Landlord

#### List Units in Property
- **Endpoint**: `GET /accounts/properties/{property_id}/units/`
- **Permissions**: Landlord

### Unit Management

#### Create Unit
- **Endpoint**: `POST /accounts/units/create/`
- **Permissions**: Landlord with active subscription
- **Body**:
  ```json
  {
    "property_obj": 1,
    "unit_number": "A1",
    "rent": 15000,
    "deposit": 15000
  }
  ```

#### Update Unit
- **Endpoint**: `PUT /accounts/units/{unit_id}/update/`
- **Permissions**: Landlord

#### Delete Unit
- **Endpoint**: `DELETE /accounts/units/{unit_id}/update/`
- **Permissions**: Landlord

#### Assign Tenant to Unit
- **Endpoint**: `POST /accounts/units/{unit_id}/assign/{tenant_id}/`
- **Permissions**: Landlord

#### Tenant Update Unit Number
- **Endpoint**: `PUT /accounts/units/tenant/update/`
- **Permissions**: Tenant
- **Body**:
  ```json
  {
    "unit_number": "New Number"
  }
  ```

### Unit Types

#### List/Create Unit Types
- **Endpoint**: `GET /accounts/unit-types/`
- **Endpoint**: `POST /accounts/unit-types/`
- **Permissions**: Landlord with active subscription

#### Detail Unit Type
- **Endpoint**: `GET /accounts/unit-types/{pk}/`
- **Endpoint**: `PUT /accounts/unit-types/{pk}/`
- **Endpoint**: `DELETE /accounts/unit-types/{pk}/`
- **Permissions**: Landlord

### Other

#### Password Reset
- **Endpoint**: `POST /accounts/password-reset/`
- **Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```

#### Password Reset Confirm
- **Endpoint**: `POST /accounts/password-reset-confirm/`
- **Body**:
  ```json
  {
    "token": "reset_token",
    "password": "new_password"
  }
  ```

#### Update M-Pesa Till Number
- **Endpoint**: `PATCH /accounts/update-till-number/`
- **Permissions**: Landlord
- **Body**:
  ```json
  {
    "mpesa_till_number": "123456"
  }
  ```

#### Adjust Rent
- **Endpoint**: `POST /accounts/adjust-rent/`
- **Permissions**: Landlord
- **Body**:
  ```json
  {
    "adjustment_type": "percentage",
    "value": 10,
    "unit_type_id": 1
  }
  ```

#### Landlord Dashboard Stats
- **Endpoint**: `GET /accounts/landlord/dashboard-stats/`
- **Permissions**: Landlord

#### Subscription Status
- **Endpoint**: `GET /accounts/subscription_status/`
- **Permissions**: Authenticated

#### Admin Landlord Subscriptions
- **Endpoint**: `GET /accounts/admin/landlord-subscriptions/`
- **Permissions**: Superuser

## Payments App Endpoints

### M-Pesa STK Push

#### Rent Payment
- **Endpoint**: `POST /payments/stk-push/{unit_id}/`
- **Permissions**: Tenant with active subscription
- **Body**:
  ```json
  {
    "amount": 15000
  }
  ```

#### Subscription Payment
- **Endpoint**: `POST /payments/stk-push-subscription/`
- **Body**:
  ```json
  {
    "plan": "starter",
    "phone_number": "+254712345678"
  }
  ```

### Callbacks (Internal)

#### Rent Callback
- **Endpoint**: `POST /payments/callback/rent/`

#### Subscription Callback
- **Endpoint**: `POST /payments/callback/subscription/`

### Payment Lists

#### Rent Payments
- **Endpoint**: `GET /payments/rent-payments/`
- **Endpoint**: `POST /payments/rent-payments/`
- **Permissions**: Authenticated with active subscription

#### Rent Payment Detail
- **Endpoint**: `GET /payments/rent-payments/{pk}/`
- **Permissions**: Authenticated with active subscription

#### Subscription Payments
- **Endpoint**: `GET /payments/subscription-payments/`
- **Endpoint**: `POST /payments/subscription-payments/`
- **Permissions**: Landlord

#### Subscription Payment Detail
- **Endpoint**: `GET /payments/subscription-payments/{pk}/`
- **Permissions**: Landlord

### Reports

#### Rent Summary
- **Endpoint**: `GET /payments/rent-payments/summary/`
- **Permissions**: Landlord

#### Landlord CSV
- **Endpoint**: `GET /payments/landlord-csv/{property_id}/`
- **Permissions**: Landlord

#### Tenant CSV
- **Endpoint**: `GET /payments/tenant-csv/{unit_id}/`
- **Permissions**: Tenant

## Communication App Endpoints

### Reports

#### Create Report
- **Endpoint**: `POST /communication/reports/`
- **Permissions**: Authenticated with active subscription
- **Body**:
  ```json
  {
    "unit": 1,
    "issue_category": "electrical",
    "priority_level": "high",
    "issue_title": "Power outage",
    "description": "No electricity in unit"
  }
  ```

#### List Reports by Status
- **Endpoint**: `GET /communication/reports/open/`
- **Endpoint**: `GET /communication/reports/urgent/`
- **Endpoint**: `GET /communication/reports/in-progress/`
- **Endpoint**: `GET /communication/reports/resolved/`
- **Permissions**: Authenticated with active subscription

#### Update Report Status
- **Endpoint**: `PUT /communication/reports/{pk}/status/`
- **Permissions**: Authenticated with active subscription
- **Body**:
  ```json
  {
    "status": "resolved"
  }
  ```

### Email

#### Send Email to Tenants
- **Endpoint**: `POST /communication/send-email/`
- **Permissions**: Landlord with active subscription
- **Body**:
  ```json
  {
    "subject": "Rent Reminder",
    "message": "Please pay your rent.",
    "send_to_all": true
  }
  ```
  or
  ```json
  {
    "subject": "Rent Reminder",
    "message": "Please pay your rent.",
    "tenants": [1, 2, 3]
  }
  ```

## Error Responses
Common error responses include:
- 400 Bad Request: Invalid data
- 401 Unauthorized: Authentication required
- 403 Forbidden: Permission denied or inactive subscription
- 404 Not Found: Resource not found
- 500 Internal Server Error: Server error

## Notes
- All endpoints requiring authentication need the `Authorization: Bearer {access_token}` header.
- Subscription checks are enforced on most endpoints to ensure only active subscribers can access features.
- M-Pesa integrations use sandbox environment for testing.
- CSV reports are cached for 5 minutes to improve performance.
