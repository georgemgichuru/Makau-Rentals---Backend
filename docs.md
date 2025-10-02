# Makau Rentals API Documentation

## Base URL
All endpoints are prefixed with the base URL of your application.

## Authentication
Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## 🔐 Authentication Endpoints

### 1. User Registration
**Endpoint:** `POST /api/accounts/signup/`  
**Description:** Create a new user account (landlord or tenant)  
**Authentication:** Not required  

**Request Body:**
```json
{
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "user_type": "landlord", // or "tenant"
    "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2024-01-15T10:30:00Z",
    "user_type": "landlord",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false
}
```

### 2. Login (JWT Token)
**Endpoint:** `POST /api/accounts/token/`  
**Description:** Obtain JWT access and refresh tokens  
**Authentication:** Not required  

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 3. Token Refresh
**Endpoint:** `POST /api/accounts/token/refresh/`  
**Description:** Refresh JWT access token  
**Authentication:** Not required  

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 4. Password Reset
**Endpoint:** `POST /api/accounts/password-reset/`  
**Description:** Request password reset email  
**Authentication:** Not required  

**Request Body:**
```json
{
    "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
    "message": "Password reset email sent."
}
```

---

## 👥 User Management Endpoints

### 5. Get User Details
**Endpoint:** `GET /api/accounts/users/{user_id}/`  
**Description:** Get details of a specific user  
**Authentication:** Required  
**Permissions:** Authenticated users  

**URL Parameters:**
- `user_id` (integer): ID of the user

**Response (200 OK):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_joined": "2024-01-15T10:30:00Z",
    "user_type": "landlord",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false
}
```

### 6. List All Users
**Endpoint:** `GET /api/accounts/users/`  
**Description:** List all tenants (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only  

**Response (200 OK):**
```json
[
    {
        "id": 2,
        "email": "tenant@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "date_joined": "2024-01-16T09:15:00Z",
        "user_type": "tenant",
        "is_active": true,
        "is_staff": false,
        "is_superuser": false
    }
]
```

### 7. Update User
**Endpoint:** `PUT /api/accounts/users/{user_id}/update/`  
**Description:** Update user details (users can only update their own profile)  
**Authentication:** Required  
**Permissions:** User can only update their own profile  

**URL Parameters:**
- `user_id` (integer): ID of the user

**Request Body (partial update allowed):**
```json
{
    "first_name": "Updated Name",
    "last_name": "Updated Last Name"
}
```

**Response (200 OK):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "Updated Name",
    "last_name": "Updated Last Name",
    "date_joined": "2024-01-15T10:30:00Z",
    "user_type": "landlord",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false
}
```

### 8. Delete User
**Endpoint:** `DELETE /api/accounts/users/{user_id}/update/`  
**Description:** Delete user account (users can only delete their own account)  
**Authentication:** Required  
**Permissions:** User can only delete their own account  

**URL Parameters:**
- `user_id` (integer): ID of the user

**Response (200 OK):**
```json
{
    "message": "User deleted successfully."
}
```

---

## 🏢 Property Management Endpoints

### 9. Create Property
**Endpoint:** `POST /api/accounts/properties/create/`  
**Description:** Create a new property (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, active subscription required  

**Request Body:**
```json
{
    "name": "Sunset Apartments",
    "city": "Nairobi",
    "state": "Nairobi County",
    "unit_count": 10
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "landlord": 1,
    "name": "Sunset Apartments",
    "city": "Nairobi",
    "state": "Nairobi County",
    "units": []
}
```

### 10. List Landlord Properties
**Endpoint:** `GET /api/accounts/properties/`  
**Description:** List all properties owned by the authenticated landlord  
**Authentication:** Required  
**Permissions:** Landlord only, active subscription required  

**Response (200 OK):**
```json
[
    {
        "id": 1,
        "landlord": 1,
        "name": "Sunset Apartments",
        "city": "Nairobi",
        "state": "Nairobi County",
        "units": [
            {
                "id": 1,
                "unit_number": "A101",
                "floor": 1,
                "bedrooms": 2,
                "bathrooms": 1,
                "rent": "25000.00",
                "tenant": null,
                "rent_paid": "0.00",
                "rent_remaining": "25000.00",
                "deposit": "50000.00",
                "is_available": true
            }
        ]
    }
]
```

### 11. Update Property
**Endpoint:** `PUT /api/accounts/properties/{property_id}/update/`  
**Description:** Update property details (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, must own the property  

**URL Parameters:**
- `property_id` (integer): ID of the property

**Request Body (partial update allowed):**
```json
{
    "name": "Updated Property Name",
    "city": "Updated City"
}
```

**Response (200 OK):**
```json
{
    "id": 1,
    "landlord": 1,
    "name": "Updated Property Name",
    "city": "Updated City",
    "state": "Nairobi County",
    "units": []
}
```

### 12. Delete Property
**Endpoint:** `DELETE /api/accounts/properties/{property_id}/update/`  
**Description:** Delete property (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, must own the property  

**URL Parameters:**
- `property_id` (integer): ID of the property

**Response (200 OK):**
```json
{
    "message": "Property deleted successfully."
}
```

---

## 🏠 Unit Management Endpoints

### 13. Create Unit
**Endpoint:** `POST /api/accounts/units/create/`  
**Description:** Create a new unit in a property (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, active subscription required  

**Request Body:**
```json
{
    "property": 1,
    "unit_number": "A101",
    "floor": 1,
    "bedrooms": 2,
    "bathrooms": 1,
    "rent": "25000.00",
    "deposit": "50000.00",
    "rent_due_date": "2024-02-01"
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "property": 1,
    "unit_number": "A101",
    "floor": 1,
    "bedrooms": 2,
    "bathrooms": 1,
    "rent": "25000.00",
    "tenant": null,
    "rent_paid": "0.00",
    "rent_remaining": "25000.00",
    "deposit": "50000.00",
    "is_available": true
}
```

### 14. Update Unit
**Endpoint:** `PUT /api/accounts/units/{unit_id}/update/`  
**Description:** Update unit details (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, must own the property containing the unit  

**URL Parameters:**
- `unit_id` (integer): ID of the unit

**Request Body (partial update allowed):**
```json
{
    "rent": "27000.00",
    "tenant": 2
}
```

**Response (200 OK):**
```json
{
    "id": 1,
    "property": 1,
    "unit_number": "A101",
    "floor": 1,
    "bedrooms": 2,
    "bathrooms": 1,
    "rent": "27000.00",
    "tenant": 2,
    "rent_paid": "0.00",
    "rent_remaining": "27000.00",
    "deposit": "50000.00",
    "is_available": false
}
```

### 15. Delete Unit
**Endpoint:** `DELETE /api/accounts/units/{unit_id}/update/`  
**Description:** Delete unit (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, must own the property containing the unit  

**URL Parameters:**
- `unit_id` (integer): ID of the unit

**Response (200 OK):**
```json
{
    "message": "Unit deleted successfully."
}
```

---

## 💰 Payment Endpoints

### 16. Initiate M-Pesa STK Push (Rent Payment)
**Endpoint:** `POST /api/payments/stk-push/{unit_id}/`  
**Description:** Initiate M-Pesa STK push for rent payment  
**Authentication:** Required  
**Permissions:** Tenant only, must be assigned to the unit  

**URL Parameters:**
- `unit_id` (integer): ID of the unit for rent payment

**Response (200 OK):**
```json
{
    "MerchantRequestID": "29115-34620561-1",
    "CheckoutRequestID": "ws_CO_191220191020363925",
    "ResponseCode": "0",
    "ResponseDescription": "Success. Request accepted for processing",
    "CustomerMessage": "Success. Request accepted for processing"
}
```

### 17. M-Pesa Rent Payment Callback
**Endpoint:** `POST /api/payments/callback/rent/`  
**Description:** M-Pesa callback for rent payments (internal use)  
**Authentication:** Not required (M-Pesa callback)  

### 18. M-Pesa Subscription Payment Callback
**Endpoint:** `POST /api/payments/callback/subscription/`  
**Description:** M-Pesa callback for subscription payments (internal use)  
**Authentication:** Not required (M-Pesa callback)  

### 19. List/Create Rent Payments
**Endpoint:** `GET|POST /api/payments/rent-payments/`  
**Description:** List rent payments or create a new rent payment  
**Authentication:** Required  

**GET Response (200 OK):**
```json
[
    {
        "id": 1,
        "tenant": 2,
        "unit": 1,
        "amount": "25000.00",
        "mpesa_receipt": "NLJ7RT61SV",
        "transaction_date": "2024-01-20T14:30:00Z",
        "status": "Success"
    }
]
```

**POST Request Body:**
```json
{
    "unit": 1,
    "amount": "25000.00"
}
```

**POST Response (201 Created):**
```json
{
    "id": 2,
    "tenant": 2,
    "unit": 1,
    "amount": "25000.00",
    "mpesa_receipt": null,
    "transaction_date": "2024-01-20T15:00:00Z",
    "status": "Pending"
}
```

### 20. Rent Payment Details
**Endpoint:** `GET /api/payments/rent-payments/{payment_id}/`  
**Description:** Get details of a specific rent payment  
**Authentication:** Required  
**Permissions:** Tenants see their own payments, landlords see payments for their properties  

**URL Parameters:**
- `payment_id` (integer): ID of the payment

**Response (200 OK):**
```json
{
    "id": 1,
    "tenant": 2,
    "unit": 1,
    "amount": "25000.00",
    "mpesa_receipt": "NLJ7RT61SV",
    "transaction_date": "2024-01-20T14:30:00Z",
    "status": "Success"
}
```

### 21. List/Create Subscription Payments
**Endpoint:** `GET|POST /api/payments/subscription-payments/`  
**Description:** List subscription payments or create a new subscription payment (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only  

**GET Response (200 OK):**
```json
[
    {
        "id": 1,
        "user": 1,
        "amount": "500.00",
        "mpesa_receipt_number": "NLJ7RT61SV",
        "transaction_date": "2024-01-15T10:00:00Z",
        "subscription_type": "basic"
    }
]
```

**POST Request Body:**
```json
{
    "amount": "500.00",
    "mpesa_receipt_number": "NLJ7RT61SV",
    "subscription_type": "basic"
}
```

### 22. Subscription Payment Details
**Endpoint:** `GET /api/payments/subscription-payments/{payment_id}/`  
**Description:** Get details of a specific subscription payment (landlord only)  
**Authentication:** Required  
**Permissions:** Landlord only, must own the payment  

**URL Parameters:**
- `payment_id` (integer): ID of the subscription payment

**Response (200 OK):**
```json
{
    "id": 1,
    "user": 1,
    "amount": "500.00",
    "mpesa_receipt_number": "NLJ7RT61SV",
    "transaction_date": "2024-01-15T10:00:00Z",
    "subscription_type": "basic"
}
```

### 23. Rent Summary
**Endpoint:** `GET /api/payments/rent-payments/summary/`  
**Description:** Get rent collection summary for landlord  
**Authentication:** Required  
**Permissions:** Landlord only  

**Response (200 OK):**
```json
{
    "landlord": "landlord@example.com",
    "total_collected": 50000.0,
    "total_outstanding": 25000.0,
    "units": [
        {
            "unit_number": "A101",
            "tenant": "tenant@example.com",
            "rent": 25000.0,
            "rent_paid": 25000.0,
            "rent_remaining": 0.0,
            "is_available": false
        },
        {
            "unit_number": "A102",
            "tenant": null,
            "rent": 25000.0,
            "rent_paid": 0.0,
            "rent_remaining": 25000.0,
            "is_available": true
        }
    ],
    "last_updated": "2024-01-20T16:00:00Z"
}
```

---

## 📧 Communication Endpoints

### 24. Trigger Tenant Reminders
**Endpoint:** `POST /api/communication/tasks/trigger/tenant-reminders/`  
**Description:** Manually trigger tenant rent reminder notifications  
**Authentication:** Required  

**Response (200 OK):**
```json
{
    "message": "Tenant reminder task triggered",
    "task_id": "celery-task-id-12345"
}
```

### 25. Trigger Landlord Summaries
**Endpoint:** `POST /api/communication/tasks/trigger/landlord-summaries/`  
**Description:** Manually trigger landlord rent summary emails  
**Authentication:** Required  

**Response (200 OK):**
```json
{
    "message": "Landlord summary task triggered",
    "task_id": "celery-task-id-67890"
}
```

---

## 📊 Subscription Management

### 26. Check Subscription Status
**Endpoint:** `GET /api/accounts/subscription_status/`  
**Description:** Check current subscription status  
**Authentication:** Required (Django session-based)  
**Permissions:** Landlord only  

**Response (200 OK):**
```
Subscription Status: Subscribed
```
or
```
Subscription Status: Inactive
```
or
```
No subscription found
```

---

## 📋 Subscription Plans & Limits

### Plan Limits
- **Free (60-day trial):** 2 properties maximum
- **Basic:** 2 properties maximum
- **Medium:** 5 properties maximum  
- **Premium:** 10 properties maximum

### Subscription Pricing (M-Pesa Amounts)
- **Basic (30 days):** KES 500
- **Premium (60 days):** KES 1,000
- **Enterprise (90 days):** KES 2,000
- **One-time (lifetime):** KES 35,000

---

## 🔒 Permission Requirements

### User Types
- **Landlord:** Can manage properties, units, view tenant payments, manage subscriptions
- **Tenant:** Can make rent payments, view their own payment history

### Subscription Requirements
Most landlord endpoints require an active subscription. The system checks:
1. User has a subscription record
2. Subscription expiry date is in the future (or null for lifetime)
3. User type is "landlord"

---

## 📝 Error Responses

### Common Error Codes
- **400 Bad Request:** Invalid input data
- **401 Unauthorized:** Authentication required
- **403 Forbidden:** Insufficient permissions or expired subscription
- **404 Not Found:** Resource not found
- **429 Too Many Requests:** Rate limit exceeded (STK Push)
- **500 Internal Server Error:** Server error

### Example Error Response
```json
{
    "error": "Your subscription has expired. Please renew or upgrade."
}
```

---

## 🚀 Rate Limiting

### STK Push Rate Limiting
- Maximum 5 requests per minute per user
- Duplicate payment prevention (5-minute window)
- Cached access tokens (55-minute expiry)

---

## 💾 Caching

The API uses Redis caching for performance optimization:
- User data: 5 minutes
- Property/Unit lists: 5 minutes  
- Payment lists: 5 minutes
- Rent summaries: 10 minutes
- M-Pesa access tokens: 55 minutes

Cache keys are automatically invalidated when related data is updated.
