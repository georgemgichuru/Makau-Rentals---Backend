# Makau Rentals

## Project Overview

**Makau Rentals** is a comprehensive apartment block management system that facilitates seamless communication and operations between landlords and tenants. The system provides automated rent collection, maintenance reporting, tenant management, and communication tools.

## Technology Stack

### Backend
- **Framework**: Django 4.2.7 with Django REST Framework 3.14.0
- **Database**: PostgreSQL 14+ (Azure Cloud)
- **Authentication**: JWT (djangorestframework-simplejwt 5.2.2)
- **Payment Integration**: M-Pesa Daraja API
- **Email**: Django Email with SMTP backend
- **Task Queue**: Celery with Redis
- **Caching**: Redis
- **File Storage**: AWS S3 (optional) or local media files
- **Documentation**: Django REST Framework browsable API

### Frontend
- **Framework**: React 18+ with JavaScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 3+
- **State Management**: React Query + Context API
- **Routing**: React Router v6
- **Forms**: React Hook Form
- **UI Components**: Headless UI + Custom components
- **HTTP Client**: Axios

### Infrastructure & Tools
- **Deployment**: Docker containers, Render
- **Web Server**: Gunicorn
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis
- **File Storage**: AWS S3 or local storage
- **Background Tasks**: Celery beat scheduler
- **API Testing**: Postman
- **Environment Management**: python-decouple

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 14+
- Redis (optional, for caching and Celery)

### Backend Setup

1. **Clone the repository and navigate to the backend directory:**
   ```bash
   cd "Makau Rentals/app"
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy and configure the required environment variables from [docs/environment_variables.md](docs/environment_variables.md)

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Run Celery worker (in a separate terminal):**
   ```bash
   celery -A app worker -l info
   ```

9. **Run Celery beat (for scheduled tasks):**
   ```bash
   celery -A app beat -l info
   ```

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd "Makao-Center-V4"
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

## File Architecture

### Backend Structure
```
Makau Rentals/app/
├── manage.py
├── app/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   ├── celery_app.py
│   └── tasks.py
├── accounts/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── permissions.py
│   └── tests.py
├── communication/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── messaging.py
│   └── tests.py
├── payments/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── generate_token.py
│   └── tests.py
├── static/
│   ├── admin/
│   └── rest_framework/
├── requirements.txt
└── logs/
```

### Frontend Structure
```
Makao-Center-V4/
├── public/
├── src/
│   ├── components/
│   │   ├── Admin/
│   │   ├── Tenant/
│   │   ├── LoginForm.jsx
│   │   ├── TenantSignUpForm.jsx
│   │   ├── Toast.jsx
│   │   └── Errors.jsx
│   ├── context/
│   ├── services/
│   └── assets/
├── package.json
├── vite.config.js
└── index.html
```

## API Endpoints

### Authentication (`/api/accounts/`)

- **POST /api/accounts/signup/**: Register a new user
- **POST /api/accounts/token/**: Obtain JWT token pair
- **POST /api/accounts/token/refresh/**: Refresh JWT token
- **GET /api/accounts/me/**: Get current user details
- **GET /api/accounts/users/**: List all users (admin)
- **GET /api/accounts/users/<int:user_id>/**: Get user by ID
- **PUT /api/accounts/users/<int:user_id>/update/**: Update user
- **POST /api/accounts/password-reset/**: Request password reset
- **POST /api/accounts/password-reset-confirm/**: Confirm password reset

### Properties (`/api/accounts/`)

- **GET /api/accounts/properties/**: List landlord's properties
- **POST /api/accounts/properties/create/**: Create new property
- **GET /api/accounts/properties/<int:property_id>/update/**: Get property for update
- **PUT /api/accounts/properties/<int:property_id>/update/**: Update property
- **GET /api/accounts/properties/<int:property_id>/units/**: Get property units

### Units (`/api/accounts/`)

- **POST /api/accounts/units/create/**: Create new unit
- **PUT /api/accounts/units/<int:unit_id>/update/**: Update unit
- **PUT /api/accounts/units/tenant/update/**: Update tenant's unit
- **PUT /api/accounts/units/<int:unit_id>/assign/<int:tenant_id>/**: Assign tenant to unit
- **GET /api/accounts/unit-types/**: List unit types
- **POST /api/accounts/unit-types/**: Create unit type
- **GET /api/accounts/unit-types/<int:pk>/**: Get unit type details
- **PUT /api/accounts/unit-types/<int:pk>/**: Update unit type
- **DELETE /api/accounts/unit-types/<int:pk>/**: Delete unit type

### Payments (`/api/payments/`)

#### Rent Payments
- **GET /api/payments/rent-payments/**: List rent payments
- **POST /api/payments/rent-payments/**: Create rent payment
- **GET /api/payments/rent-payments/<int:pk>/**: Get rent payment details
- **PUT /api/payments/rent-payments/<int:pk>/**: Update rent payment
- **DELETE /api/payments/rent-payments/<int:pk>/**: Delete rent payment

#### Subscription Payments
- **GET /api/payments/subscription-payments/**: List subscription payments
- **POST /api/payments/subscription-payments/**: Create subscription payment
- **GET /api/payments/subscription-payments/<int:pk>/**: Get subscription payment details
- **PUT /api/payments/subscription-payments/<int:pk>/**: Update subscription payment
- **DELETE /api/payments/subscription-payments/<int:pk>/**: Delete subscription payment

#### M-Pesa Integration
- **POST /api/payments/stk-push/<int:unit_id>/**: Initiate rent STK push
- **POST /api/payments/stk-push-subscription/**: Initiate subscription STK push
- **POST /api/payments/initiate-deposit/**: Initiate deposit payment
- **GET /api/payments/deposit-status/<int:payment_id>/**: Check deposit status
- **GET /api/payments/rent-payments/summary/**: Get rent summary
- **GET /api/payments/unit-types/**: List payment unit types

#### Callbacks (M-Pesa)
- **POST /api/payments/callback/rent/**: Rent payment callback
- **POST /api/payments/callback/subscription/**: Subscription payment callback
- **POST /api/payments/callback/deposit/**: Deposit payment callback
- **POST /api/payments/callback/b2c/**: B2C payment callback

#### Reports & Cleanup
- **GET /api/payments/landlord-csv/<int:property_id>/**: Download landlord CSV report
- **GET /api/payments/tenant-csv/<int:unit_id>/**: Download tenant CSV report
- **POST /api/payments/cleanup-pending-payments/**: Clean up pending payments
- **GET /api/payments/test-mpesa/**: Test M-Pesa integration

### Communication (`/api/communication/`)

#### Reports
- **POST /api/communication/reports/create/**: Create maintenance report
- **GET /api/communication/reports/open/**: List open reports
- **GET /api/communication/reports/urgent/**: List urgent reports
- **GET /api/communication/reports/in-progress/**: List in-progress reports
- **GET /api/communication/reports/resolved/**: List resolved reports
- **PUT /api/communication/reports/<int:pk>/update-status/**: Update report status

#### Email
- **POST /api/communication/reports/send-email/**: Send email to tenants

## Documentation

- [Environment Variables Setup](docs/environment_variables.md)
- [Migration Plan](docs/migration_plan.md)
- [M-Pesa Callback URLs](docs/mpesa_callback_urls.md)

## Deployment

The application is configured for deployment on Render with:
- PostgreSQL database
- Redis for caching and Celery
- Static file serving with WhiteNoise
- Automatic superuser creation on first run

For detailed deployment instructions, refer to the environment variables documentation.

## Development

### Running Tests
```bash
# Backend tests
cd "Makau Rentals/app"
python manage.py test

# Frontend tests (if configured)
cd "Makao-Center-V4"
npm test
```

### Code Quality
- Follow Django best practices
- Use Black for Python code formatting
- ESLint for JavaScript/React code
- Pre-commit hooks recommended

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.
