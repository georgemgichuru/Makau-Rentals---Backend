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