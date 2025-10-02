# Makau Rentals

## Project Overview

**Makao Rentals** is a comprehensive apartment block management system that facilitates seamless communication and operations between landlords and tenants. The system provides automated rent collection, maintenance reporting, tenant management, and communication tools.

## Technology Stack

### Backend
- **Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL 14+ in cloud AZURE
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Payment Integration**: M-Pesa Daraja API
- **Email**: Django Email with SMTP backend
- **Documentation**: Django REST Swagger
### Frontend
- **Framework**: React 18+ with javascript
- **Styling**: Tailwind CSS 3+
- **State Management**: React Query + Context API
- **Routing**: React Router v6
- **Forms**: React Hook Form
- **UI Components**: Headless UI + Custom components
- **HTTP Client**: Axios

### Infrastructure & Tools
- **Deployment**: Docker containers
- **Web Server**: Nginx
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis
- **File Storage**: Cloud storage solution
- **CI/CD**: Jenkins
- **API Testing**: Postman (Frontend to use some mock servers)

## File architecture

### Backend side

```
makao_rentals_backend/
├── manage.py
├── makao_rentals/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── tenants/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── landlords/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── payments/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── maintenance/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   └── communication/
│       ├── models.py
│       ├── views.py
│       ├── serializers.py
│       └── urls.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```
### Project Plan
For a detailed project plan, refer to [makau_rentals_plan.md](makao_rentals_plan.md).

### Project Timeline

The project timeline is as follows:

| Week | Task |
| --- | --- |
| 1   | Set up project infrastructure (Docker, Nginx, PostgreSQL, Redis) |
| 2   | Set up frontend (React, Tailwind CSS, React Query) |
| 3   | Set up backend (Django, Django Rest Framework, React Hook Form) |
| 4   | Implement authentication and authorization |
| 5   | Implement CRUD operations for landlords and tenants |
| 6   | Implement CRUD operations for properties, units and payments |
| 7   | Implement communication features (email, SMS) |
| 8   | Implement maintenance features (background tasks, notifications) |
| 9   | Test and debug the application |
| 10  | Deploy the application to production |
| 11  | Test and debug the application in production |
| 12  | Hand over the application to the client |

### URL Endpoints

#### Authentication

- **POST /api/v1/auth/token/obtain/**: Obtain a JWT token for authentication
- **POST /api/v1/auth/token/refresh/**: Refresh a JWT token
- **POST /api/v1/auth/password/reset/**: Reset a user's password

#### Landlords

- **GET /api/v1/landlords/**: Get a list of all landlords
- **GET /api/v1/landlords/<int:landlord_id>/**: Get a landlord by ID
- **POST /api/v1/landlords/**: Create a new landlord
- **PUT /api/v1/landlords/<int:landlord_id>/**: Update a landlord
- **DELETE /api/v1/landlords/<int:landlord_id>/**: Delete a landlord

#### Tenants

- **GET /api/v1/tenants/**: Get a list of all tenants
- **GET /api/v1/tenants/<int:tenant_id>/**: Get a tenant by ID
- **POST /api/v1/tenants/**: Create a new tenant
- **PUT /api/v1/tenants/<int:tenant_id>/**: Update a tenant
- **DELETE /api/v1/tenants/<int:tenant_id>/**: Delete a tenant

#### Properties

- **GET /api/v1/properties/**: Get a list of all properties
- **GET /api/v1/properties/<int:property_id>/**: Get a property by ID
- **POST /api/v1/properties/**: Create a new property
- **PUT /api/v1/properties/<int:property_id>/**: Update a property
- **DELETE /api/v1/properties/<int:property_id>/**: Delete a property

#### Units

- **GET /api/v1/units/**: Get a list of all units
- **GET /api/v1/units/<int:unit_id>/**: Get a unit by ID
- **POST /api/v1/units/**: Create a new unit
- **PUT /api/v1/units/<int:unit_id>/**: Update a unit
- **DELETE /api/v1/units/<int:unit_id>/**: Delete a unit

#### Payments
/*******  7969e49b-aba0-4acb-be82-d43bc92b85ad  *******/
- **GET /api/v1/payments/<int:payment_id>/**: Get a payment by ID
- **POST /api/v1/payments/**: Create a new payment
- **PUT /api/v1/payments/<int:payment_id>/**: Update a payment
- **DELETE /api/v1/payments/<int:payment_id>/**: Delete a payment
/*************  ✨ Windsurf Command ⭐  *************/
#### Subscription Payments

- **GET /api/v1/subscription_payments/**: Get a list of all subscription payments
- **GET /api/v1/subscription_payments/<int:subscription_payment_id>/**: Get a subscription payment by ID
- **POST /api/v1/subscription_payments/**: Create a new subscription payment
- **PUT /api/v1/subscription_payments/<int:subscription_payment_id>/**: Update a subscription payment
- **DELETE /api/v1/subscription_payments/<int:subscription_payment_id>/**: Delete a subscription payment

#### Communication
- **POST /api/v1/communication/email/**: Send an email to a user. This endpoint takes in a JSON payload containing the email address of the recipient and the email content. The email content should be a JSON object with the keys "subject" and "body".
- **POST /api/v1/communication/sms/**: Send an SMS to a user. This endpoint takes in a JSON payload containing the phone number of the recipient and the SMS content. The SMS content should be a JSON object with the key "message".

For more documentation on the endpoints read [docs.md]