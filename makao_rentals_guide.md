# Makao Rentals - Complete Development Guide

## Project Overview

**Makao Rentals** is a comprehensive apartment block management system that facilitates seamless communication and operations between landlords and tenants. The system provides automated rent collection, maintenance reporting, tenant management, and communication tools.

## Technology Stack

### Backend
- **Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL 14+
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Payment Integration**: M-Pesa Daraja API
- **File Storage**: Django storages with cloud storage (AWS S3/DigitalOcean Spaces)
- **Email**: Django Email with SMTP backend
- **Documentation**: Django REST Swagger

### Frontend
- **Framework**: React 18+ with TypeScript
- **Styling**: Tailwind CSS 3+
- **State Management**: React Query + Context API
- **Routing**: React Router v6
- **Forms**: React Hook Form
- **UI Components**: Headless UI + Custom components
- **HTTP Client**: Axios

### Infrastructure
- **Deployment**: Docker containers
- **Web Server**: Nginx
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis
- **File Storage**: Cloud storage solution

---

## Database Schema Design

### User Management

```sql
-- Custom User Model
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    government_id VARCHAR(50) UNIQUE NOT NULL,
    emergency_contact VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    is_staff BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    password_hash VARCHAR(255) NOT NULL
);

-- User Roles
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL, -- 'landlord', 'tenant'
    permissions JSONB
);

-- User Role Assignment
CREATE TABLE user_role_assignments (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES user_roles(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Property Management

```sql
-- Buildings/Apartment Blocks
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(10),
    landlord_id UUID REFERENCES users(id),
    total_units INTEGER NOT NULL,
    kplc_account_number VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Units/Rooms
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    building_id INTEGER REFERENCES buildings(id) ON DELETE CASCADE,
    unit_number VARCHAR(10) NOT NULL,
    unit_type VARCHAR(50) NOT NULL, -- 'studio', '1br', '2br', etc.
    rent_amount DECIMAL(10,2) NOT NULL,
    deposit_amount DECIMAL(10,2) NOT NULL,
    is_occupied BOOLEAN DEFAULT false,
    floor_number INTEGER,
    square_footage DECIMAL(8,2),
    amenities JSONB, -- JSON array of amenities
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(building_id, unit_number)
);

-- Tenancy Agreements
CREATE TABLE tenancies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES users(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE,
    rent_amount DECIMAL(10,2) NOT NULL,
    deposit_amount DECIMAL(10,2) NOT NULL,
    deposit_paid BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'terminated', 'expired'
    lease_document VARCHAR(500), -- File path
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Financial Management

```sql
-- Rent Invoices
CREATE TABLE rent_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenancy_id UUID REFERENCES tenancies(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'paid', 'overdue', 'cancelled'
    late_fee DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES rent_invoices(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- 'mpesa', 'bank_transfer'
    transaction_id VARCHAR(100) UNIQUE,
    mpesa_receipt_number VARCHAR(50),
    payment_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'failed'
    mpesa_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Maintenance & Reports

```sql
-- Issue Categories
CREATE TABLE issue_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- 'electrical', 'plumbing', 'noise', etc.
    priority_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    estimated_resolution_hours INTEGER DEFAULT 24
);

-- Maintenance Reports
CREATE TABLE maintenance_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES users(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES issue_categories(id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'in_progress', 'resolved', 'closed'
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    assigned_to UUID REFERENCES users(id), -- Maintenance staff
    attachments JSONB, -- Array of file paths
    landlord_notes TEXT,
    tenant_satisfaction_rating INTEGER CHECK (tenant_satisfaction_rating >= 1 AND tenant_satisfaction_rating <= 5),
    estimated_cost DECIMAL(10,2),
    actual_cost DECIMAL(10,2)
);
```

### Communication System

```sql
-- Announcements
CREATE TABLE announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id UUID REFERENCES users(id) ON DELETE CASCADE,
    building_id INTEGER REFERENCES buildings(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high'
    target_audience VARCHAR(20) DEFAULT 'all', -- 'all', 'specific_units'
    target_units INTEGER[] DEFAULT '{}', -- Array of unit IDs
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Notification Log
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'rent_due', 'maintenance', 'announcement'
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);
```

---

## Django Backend Architecture

### Project Structure

```
makao_rentals/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── authentication/
│   ├── users/
│   ├── properties/
│   ├── financials/
│   ├── maintenance/
│   ├── communications/
│   └── common/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── static/
├── media/
├── templates/
└── manage.py
```

### Key Models (Django)

```python
# apps/users/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
import uuid

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    government_id = models.CharField(max_length=50, unique=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']

# apps/properties/models.py
class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE)
    total_units = models.IntegerField()
    kplc_account_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Unit(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    unit_number = models.CharField(max_length=10)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_occupied = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['building', 'unit_number']
```

### API Endpoints Structure

```python
# Main URL patterns
api/v1/
├── auth/
│   ├── login/
│   ├── refresh/
│   ├── logout/
│   └── register/
├── users/
│   ├── profile/
│   ├── tenants/
│   └── landlords/
├── properties/
│   ├── buildings/
│   ├── units/
│   └── tenancies/
├── financials/
│   ├── invoices/
│   ├── payments/
│   └── mpesa/callback/
├── maintenance/
│   ├── reports/
│   ├── categories/
│   └── status/
└── communications/
    ├── announcements/
    └── notifications/
```

### JWT Authentication Setup

```python
# settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# apps/authentication/serializers.py
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        user = authenticate(
            request=self.context.get('request'),
            username=attrs['email'],
            password=attrs['password']
        )
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        attrs['user'] = user
        return attrs
```

---

## Frontend Architecture (React + TypeScript)

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── forms/
│   │   ├── layout/
│   │   └── ui/
│   ├── pages/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── tenant/
│   │   └── landlord/
│   ├── hooks/
│   ├── services/
│   ├── utils/
│   ├── types/
│   ├── context/
│   └── App.tsx
├── public/
├── tailwind.config.js
└── package.json
```

### Key Types (TypeScript)

```typescript
// types/user.ts
export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  phoneNumber: string;
  governmentId: string;
  role: 'landlord' | 'tenant';
}

// types/property.ts
export interface Unit {
  id: number;
  unitNumber: string;
  rentAmount: number;
  isOccupied: boolean;
  building: Building;
}

// types/financial.ts
export interface Invoice {
  id: string;
  amount: number;
  dueDate: string;
  status: 'pending' | 'paid' | 'overdue';
  billingPeriod: {
    start: string;
    end: string;
  };
}
```

---

## Frontend Page Designs & Structure

### 1. Authentication Pages

**Login Page**
- Clean, centered form with company branding
- Email and password fields
- "Remember me" checkbox
- Forgot password link
- Modern gradient background with apartment imagery

**Registration Page (Admin Only)**
- Multi-step form for tenant registration
- File upload for tenant documents (PDF)
- Form validation with real-time feedback
- Progress indicator

### 2. Landlord Dashboard

**Main Dashboard**
- Key metrics cards (Total Units, Occupancy Rate, Monthly Revenue, Outstanding Rent)
- Recent payments table
- Maintenance requests summary
- Quick action buttons

**Tenant Management**
- Searchable tenant list with filters
- Add new tenant modal
- Bulk email functionality
- Individual tenant detail views

**Financial Overview**
- Revenue charts and analytics
- Outstanding payments list
- Payment history
- Export functionality

**Property Management**
- Building overview with unit grid
- Unit status indicators (occupied/vacant)
- Rent pricing management
- Maintenance scheduling

### 3. Tenant Portal

**Tenant Dashboard**
- Current rent status
- Next payment due date
- Unit information card
- Recent announcements

**Payment Section**
- Payment history
- Current outstanding balance
- M-Pesa payment integration
- Receipt downloads

**Maintenance Requests**
- Submit new request form
- Track existing requests
- Upload photos for issues
- Rate completed services

**Profile Management**
- View personal information
- Update contact details
- View lease agreement
- Emergency contact information

---

## M-Pesa Integration Guide

### Setup Requirements

1. **M-Pesa Developer Account**
   - Register at developer.safaricom.co.ke
   - Create app and get Consumer Key & Secret
   - Configure callback URLs

2. **Django Integration**

```python
# apps/financials/mpesa.py
import base64
import requests
from datetime import datetime
from django.conf import settings

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = settings.MPESA_BASE_URL
        
    def get_access_token(self):
        auth_string = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_string}'
        }
        
        response = requests.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers=headers
        )
        return response.json().get('access_token')
    
    def stk_push(self, phone_number, amount, account_reference):
        access_token = self.get_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
        ).decode()
        
        payload = {
            'BusinessShortCode': settings.MPESA_SHORTCODE,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': amount,
            'PartyA': phone_number,
            'PartyB': settings.MPESA_SHORTCODE,
            'PhoneNumber': phone_number,
            'CallBackURL': settings.MPESA_CALLBACK_URL,
            'AccountReference': account_reference,
            'TransactionDesc': f'Rent payment for {account_reference}'
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )
        return response.json()
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)
- Set up development environment
- Database design and migrations
- User authentication system
- Basic CRUD operations for properties
- Frontend project setup with routing

### Phase 2: Core Features (Weeks 4-7)
- Tenant management system
- Rent invoice generation
- Basic payment recording
- Maintenance request system
- Landlord dashboard

### Phase 3: Payment Integration (Weeks 8-10)
- M-Pesa STK Push integration
- Payment callback handling
- Automated invoice generation
- Payment history and receipts

### Phase 4: Enhanced Features (Weeks 11-13)
- Email notification system
- Announcement system
- File upload handling
- Advanced reporting and analytics
- Mobile responsiveness optimization

### Phase 5: Testing & Deployment (Weeks 14-16)
- Comprehensive testing
- Performance optimization
- Security audit
- Production deployment
- Documentation completion

---

## Security Considerations

### Backend Security
- JWT token management and rotation
- Input validation and sanitization
- SQL injection prevention
- Rate limiting on API endpoints
- CORS configuration
- Environment variable management
- File upload security

### Frontend Security
- XSS prevention
- Secure token storage
- Input validation
- HTTPS enforcement
- Content Security Policy

---

## Performance Optimization

### Backend
- Database indexing strategy
- Query optimization
- Caching with Redis
- Connection pooling
- Background task processing with Celery

### Frontend
- Code splitting and lazy loading
- Image optimization
- Bundle size optimization
- Caching strategies
- Progressive Web App features

---

## Deployment Architecture

### Production Setup
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
  
  backend:
    build: ./backend
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/makao_rentals
    depends_on:
      - db
      - redis
  
  frontend:
    build: ./frontend
    environment:
      - REACT_APP_API_URL=https://api.makaorentals.com
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=makao_rentals
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine
```

---

## Monitoring & Maintenance

### Logging Strategy
- Structured logging with JSON format
- Centralized log collection
- Error tracking with Sentry
- Performance monitoring

### Backup Strategy
- Daily database backups
- File storage backups
- Configuration backups
- Backup retention policy

---

## Future Enhancements

### Phase 2 Features
- Mobile app (React Native)
- Advanced analytics and reporting
- Integration with accounting software
- Automated late fee calculation
- Tenant screening integration
- Document management system
- Multi-building support for large landlords

### Scalability Considerations
- Microservices architecture migration
- Event-driven architecture
- Real-time notifications with WebSockets
- Multi-tenancy support
- API versioning strategy

---

## Cost Estimates

### Development Costs
- Backend Development: 120-150 hours
- Frontend Development: 100-120 hours
- M-Pesa Integration: 20-30 hours
- Testing & QA: 40-50 hours
- Deployment & DevOps: 20-30 hours

### Operational Costs (Monthly)
- Cloud hosting: $50-100
- Database hosting: $30-50
- File storage: $10-20
- Email service: $10-20
- M-Pesa transaction fees: Variable
- SSL certificates: $10-20
- Monitoring tools: $20-40

---

This comprehensive guide provides a solid foundation for building a scalable, future-proof apartment management system. Each section can be expanded based on specific requirements and client feedback.