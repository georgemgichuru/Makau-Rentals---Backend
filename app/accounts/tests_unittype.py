from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import UnitType, Property, Unit
from payments.models import Payment

CustomUser = get_user_model()

class UnitTypeAndUnitCreationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        # Subscription is auto-created, don't create manually
        self.client.force_authenticate(user=self.landlord)
        
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            city='Nairobi',
            state='Nairobi County',
            unit_count=10
        )

    def test_create_unittype_and_then_unit(self):
        """Test creating unit type and then unit"""
        # Create unit type first
        unit_type_data = {
            'name': 'Studio',
            'deposit': '5000.00',
            'rent': '15000.00'
        }
        response = self.client.post(reverse('unit-types'), unit_type_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        unit_type_id = response.data['id']

        # Then create unit
        unit_data = {
            'property': self.property.id,
            'unit_type': unit_type_id,
            'floor': 1,
            'bedrooms': 1,
            'bathrooms': 1
        }
        response = self.client.post(reverse('unit-create'), unit_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_create_unit_without_unittype(self):
        """Test that unit creation fails without unit type"""
        unit_data = {
            'property': self.property.id,
            'floor': 1,
            'bedrooms': 1,
            'bathrooms': 1
        }
        response = self.client.post(reverse('unit-create'), unit_data)
        # Should fail because unit_type is required
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TenantSignupAssignTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        # Subscription is auto-created
        
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            city='Nairobi',
            state='Nairobi County',
            unit_count=10
        )
        
        self.unit_type = UnitType.objects.create(
            landlord=self.landlord,
            name='Studio',
            deposit=5000,
            rent=15000
        )
        
        self.unit = Unit.objects.create(
            property_obj=self.property,
            unit_type=self.unit_type,
            unit_number='101',
            unit_code='U-101',
            rent=15000,
            deposit=5000,
            is_available=True
        )

    def test_tenant_signup_assign_after_deposit(self):
        """Test tenant signup and assignment after deposit payment"""
        # Tenant signs up with landlord code
        tenant_data = {
            'email': 'tenant@test.com',
            'full_name': 'Test Tenant',
            'user_type': 'tenant',
            'password': 'testpass123',
            'landlord_code': self.landlord.landlord_code,
            'phone_number': '+254712345678'
        }
        response = self.client.post(reverse('signup'), tenant_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tenant_id = response.data['id']
        
        # Get the created tenant
        tenant = CustomUser.objects.get(id=tenant_id)
        
        # Simulate deposit payment
        payment = Payment.objects.create(
            tenant=tenant,
            unit=self.unit,
            payment_type='deposit',
            amount=5000,
            status='Success',
            mpesa_receipt='TEST123456'
        )
        
        # Unit should be assigned to tenant
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.tenant, tenant)
        self.assertFalse(self.unit.is_available)
