# accounts/tests_subscription.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from .models import Subscription, Property

User = get_user_model()


class SubscriptionModelTests(TestCase):
    def setUp(self):
        # Create landlord without triggering automatic subscription
        self.landlord = User.objects.create(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        # Manually create subscription to avoid manager auto-creation
        self.subscription = Subscription.objects.create(
            user=self.landlord,
            plan='starter',
            expiry_date=timezone.now() + timedelta(days=30)
        )

    def test_subscription_creation(self):
        """Test creating a subscription"""
        self.assertEqual(self.subscription.user, self.landlord)
        self.assertEqual(self.subscription.plan, 'starter')
        self.assertTrue(self.subscription.is_active())

    def test_free_trial_subscription(self):
        """Test free trial subscription creation"""
        # Create a new landlord for this test
        new_landlord = User.objects.create(
            email='new_landlord@test.com',
            full_name='New Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        subscription = Subscription.objects.create(
            user=new_landlord,
            plan='free'
        )
        
        # Should automatically set expiry date to 60 days from now
        self.assertIsNotNone(subscription.expiry_date)
        expected_expiry = timezone.now() + timedelta(days=60)
        self.assertAlmostEqual(
            subscription.expiry_date.timestamp(),
            expected_expiry.timestamp(),
            delta=10  # 10 seconds tolerance
        )

    def test_subscription_is_active(self):
        """Test subscription active status"""
        # Active subscription
        self.assertTrue(self.subscription.is_active())
        
        # Expired subscription
        expired_landlord = User.objects.create(
            email='expired@test.com',
            full_name='Expired Landlord',
            user_type='landlord',
            password='testpass123'
        )
        expired_sub = Subscription.objects.create(
            user=expired_landlord,
            plan='starter',
            expiry_date=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(expired_sub.is_active())
        
        # Lifetime subscription (no expiry)
        lifetime_landlord = User.objects.create(
            email='lifetime@test.com',
            full_name='Lifetime Landlord',
            user_type='landlord',
            password='testpass123'
        )
        lifetime_sub = Subscription.objects.create(
            user=lifetime_landlord,
            plan='onetime',
            expiry_date=None
        )
        self.assertTrue(lifetime_sub.is_active())

    def test_subscription_string_representation(self):
        """Test subscription string representation"""
        expected_str = f"{self.landlord.email} - starter"
        self.assertEqual(str(self.subscription), expected_str)

from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import Subscription, Property, Unit

CustomUser = get_user_model()

class SubscriptionViewTests(APITestCase):
    def setUp(self):
        # Create landlord user with required full_name
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            password='testpass123',
            full_name='Test Landlord',  # Add this required field
            user_type='landlord'
        )
        # Create subscription for landlord
        self.subscription = Subscription.objects.create(
            user=self.landlord,
            subscription_type='free_trial',
            is_active=True
        )
        
        # Create property for testing
        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Test Property',
            address='123 Test St'
        )
        
    def test_subscription_status_view(self):
        """Test subscription status endpoint"""
        # Authenticate the request
        self.client.force_authenticate(user=self.landlord)
        
        url = reverse('subscription-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Add more assertions to check the response data
        self.assertIn('plan', response.data)
        self.assertIn('is_active', response.data)
    
    def test_property_creation_with_subscription(self):
        """Test property creation respects subscription limits"""
        # Authenticate the request
        self.client.force_authenticate(user=self.landlord)
        
        url = reverse('property-create')
        data = {
            'name': 'Test Property 2',
            'address': '456 Test Ave',
        }
        response = self.client.post(url, data, format='json')
        
        # For free trial with limit of 2 properties, first property should succeed
        current_property_count = Property.objects.filter(landlord=self.landlord).count()
        if current_property_count < 2:  # free trial allows 2 properties
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)