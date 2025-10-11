# payments/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

from accounts.models import Property, Unit, UnitType, Subscription
from .models import Payment, SubscriptionPayment

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        
        self.tenant = User.objects.create_user(
            email='tenant@test.com',
            full_name='Test Tenant',
            user_type='tenant',
            password='testpass123'
        )
        
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            city='Nairobi',
            state='Nairobi County',
            unit_count=5
        )
        
        self.unit_type = UnitType.objects.create(
            landlord=self.landlord,
            name='Studio',
            rent=Decimal('15000.00'),
            deposit=Decimal('15000.00')
        )
        
        self.unit = Unit.objects.create(
            property_obj=self.property,
            unit_number='101',
            unit_type=self.unit_type,
            rent=Decimal('15000.00'),
            deposit=Decimal('15000.00'),
            tenant=self.tenant,
            is_available=False
        )

    def test_payment_creation(self):
        """Test creating a rent payment"""
        payment = Payment.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            payment_type='rent',
            amount=Decimal('15000.00'),
            status='Success'
        )
        
        self.assertEqual(payment.tenant, self.tenant)
        self.assertEqual(payment.unit, self.unit)
        self.assertEqual(payment.payment_type, 'rent')
        self.assertEqual(payment.amount, Decimal('15000.00'))
        self.assertEqual(payment.status, 'Success')
        self.assertIsNotNone(payment.transaction_date)

    def test_payment_save_updates_unit_rent(self):
        """Test that successful rent payment updates unit rent_paid"""
        payment = Payment.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            payment_type='rent',
            amount=Decimal('10000.00'),
            status='Success'
        )
        
        # Refresh unit from database
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.rent_paid, Decimal('10000.00'))
        self.assertEqual(self.unit.rent_remaining, Decimal('5000.00'))

    def test_deposit_payment_creation(self):
        """Test creating a deposit payment"""
        payment = Payment.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            payment_type='deposit',
            amount=Decimal('15000.00'),
            status='Success'
        )
        
        self.assertEqual(payment.payment_type, 'deposit')
        self.assertEqual(payment.amount, Decimal('15000.00'))

    def test_payment_string_representation(self):
        """Test payment string representation"""
        payment = Payment.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            payment_type='rent',
            amount=Decimal('15000.00'),
            status='Success'
        )
        
        expected_str = f"{self.tenant.email} - Unit {self.unit.unit_number} - KES 15000.00 (Success)"
        self.assertEqual(str(payment), expected_str)


class SubscriptionPaymentModelTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )

    def test_subscription_payment_creation(self):
        """Test creating a subscription payment"""
        subscription_payment = SubscriptionPayment.objects.create(
            user=self.landlord,
            amount=Decimal('2000.00'),
            mpesa_receipt_number='TEST123456',
            subscription_type='starter'
        )
        
        self.assertEqual(subscription_payment.user, self.landlord)
        self.assertEqual(subscription_payment.amount, Decimal('2000.00'))
        self.assertEqual(subscription_payment.mpesa_receipt_number, 'TEST123456')
        self.assertEqual(subscription_payment.subscription_type, 'starter')
        self.assertIsNotNone(subscription_payment.transaction_date)

    def test_subscription_payment_save_updates_subscription(self):
        """Test that subscription payment updates user subscription"""
        subscription_payment = SubscriptionPayment.objects.create(
            user=self.landlord,
            amount=Decimal('2000.00'),
            mpesa_receipt_number='TEST123456',
            subscription_type='starter'
        )
        
        # Check that subscription was created/updated
        subscription = Subscription.objects.get(user=self.landlord)
        self.assertEqual(subscription.plan, 'starter')
        self.assertIsNotNone(subscription.expiry_date)

    def test_subscription_payment_string_representation(self):
        """Test subscription payment string representation"""
        subscription_payment = SubscriptionPayment.objects.create(
            user=self.landlord,
            amount=Decimal('2000.00'),
            mpesa_receipt_number='TEST123456',
            subscription_type='starter'
        )
        
        expected_str = f"{self.landlord.email} - starter - TEST123456"
        self.assertEqual(str(subscription_payment), expected_str)

from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from payments.models import Payment, SubscriptionPayment
from accounts.models import Property, Unit, Subscription

CustomUser = get_user_model()

class PaymentViewTests(APITestCase):
    def setUp(self):
        # Create users
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            password='testpass123',
            user_type='landlord'
        )
        self.tenant = CustomUser.objects.create_user(
            email='tenant@test.com',
            password='testpass123', 
            user_type='tenant'
        )
        
        # Create subscription for landlord
        self.subscription = Subscription.objects.create(
            user=self.landlord,
            subscription_type='free_trial',
            is_active=True
        )
        
        # Create property and unit
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            address='123 Test St'
        )
        self.unit = Unit.objects.create(
            property_obj=self.property,
            unit_number='101',
            unit_code='U-101',
            rent=5000,
            deposit=5000
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            amount=5000,
            payment_type='rent',
            status='Success'
        )
    
    def test_payment_list_view_tenant(self):
        """Test tenant can view their payments"""
        self.client.force_authenticate(user=self.tenant)
        
        url = reverse('payment-list')  # This should exist in payments/urls.py
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_payment_list_view_landlord(self):
        """Test landlord can view payments for their properties"""
        self.client.force_authenticate(user=self.landlord)
        
        url = reverse('payment-list')  # This should exist in payments/urls.py
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_payment_detail_view(self):
        """Test payment detail view"""
        self.client.force_authenticate(user=self.landlord)
        
        url = reverse('payment-detail', kwargs={'pk': self.payment.id})  # This should exist in payments/urls.py
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SubscriptionPaymentViewTests(APITestCase):
    def setUp(self):
        self.landlord = get_user_model().objects.create_user(
            email='landlord@test.com',
            password='testpass123',
            user_type='landlord',
            phone_number='+254712345678'
        )
        # Create subscription for the landlord
        from accounts.models import Subscription
        self.subscription = Subscription.objects.create(
            user=self.landlord,
            subscription_type='premium',
            is_active=True
        )
        
    def test_stk_push_subscription_payment(self):
        """Test STK push initiation for subscription payment"""
        self.client.force_authenticate(user=self.landlord)
        
        url = reverse('stk-push-subscription')
        data = {
            'phone_number': '+254712345678',
            'amount': 1000
        }
        
        # Mock the M-Pesa API call
        with patch('payments.views.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                'ResponseCode': '0',
                'ResponseDescription': 'Success',
                'CheckoutRequestID': 'test123'
            }
            mock_post.return_value.status_code = 200
            
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

class MPESACallbackTests(APITestCase):
    def test_subscription_callback_success(self):
        """Test successful subscription payment callback"""
        callback_data = {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': 'test123',
                    'CheckoutRequestID': 'test456', 
                    'ResultCode': 0,
                    'ResultDesc': 'Success',
                    'CallbackMetadata': {
                        'Item': [
                            {'Name': 'Amount', 'Value': 1000},
                            {'Name': 'MpesaReceiptNumber', 'Value': 'TEST123456'},
                            {'Name': 'PhoneNumber', 'Value': '254712345678'}
                        ]
                    }
                }
            }
        }
        
        url = reverse('subscription-callback')  # Use the correct URL name
        response = self.client.post(url, callback_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class RentSummaryViewTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        
        self.tenant = User.objects.create_user(
            email='tenant@test.com',
            full_name='Test Tenant',
            user_type='tenant',
            password='testpass123'
        )
        
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            city='Nairobi',
            state='Nairobi County',
            unit_count=5
        )
        
        self.unit = Unit.objects.create(
            property_obj=self.property,
            unit_number='101',
            rent=Decimal('15000.00'),
            deposit=Decimal('15000.00'),
            tenant=self.tenant,
            is_available=False
        )

    def test_rent_summary_view(self):
        """Test rent summary view for landlord"""
        self.client.force_login(self.landlord)
        response = self.client.get('/api/payments/rent-payments/summary/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('total_collected', data)
        self.assertIn('total_outstanding', data)
        self.assertIn('units', data)


class InitiateDepositPaymentTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        
        self.tenant = User.objects.create_user(
            email='tenant@test.com',
            full_name='Test Tenant',
            user_type='tenant',
            password='testpass123'
        )
        
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            city='Nairobi',
            state='Nairobi County',
            unit_count=5
        )
        
        self.unit = Unit.objects.create(
            property_obj=self.property,
            unit_number='101',
            rent=Decimal('15000.00'),
            deposit=Decimal('15000.00'),
            is_available=True
        )

    @patch('payments.views.generate_access_token')
    @patch('payments.views.requests.post')
    def test_initiate_deposit_payment(self, mock_post, mock_token):
        """Test initiating deposit payment"""
        mock_token.return_value = 'test_token'
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'ResponseCode': '0',
            'ResponseDescription': 'Success'
        }
        mock_post.return_value = mock_response
        
        self.client.force_login(self.tenant)
        data = {'unit_id': self.unit.id}
        response = self.client.post('/api/payments/initiate-deposit/', data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('ResponseCode', response.json())