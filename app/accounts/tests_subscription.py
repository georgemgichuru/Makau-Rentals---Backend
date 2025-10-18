from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Subscription, Property

CustomUser = get_user_model()

class SubscriptionModelTests(TestCase):
    def test_subscription_creation(self):
        """Test creating a subscription"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            user_type='landlord',
            password='testpass123'
        )
        # Subscription should be auto-created, so we get it instead of creating
        subscription = Subscription.objects.get(user=user)
        self.assertEqual(subscription.plan, 'free')
        self.assertTrue(subscription.is_active())

    def test_free_trial_subscription(self):
        """Test free trial subscription creation"""
        user = CustomUser.objects.create_user(
            email='trial@example.com',
            full_name='Trial User',
            user_type='landlord',
            password='testpass123'
        )
        # Subscription should be automatically created
        self.assertTrue(hasattr(user, 'subscription'))
        self.assertEqual(user.subscription.plan, 'free')

    def test_subscription_is_active(self):
        """Test subscription active status"""
        user = CustomUser.objects.create_user(
            email='active@example.com',
            full_name='Active User',
            user_type='landlord',
            password='testpass123'
        )
        subscription = user.subscription
        subscription.expiry_date = timezone.now() + timedelta(days=30)
        subscription.save()
        self.assertTrue(subscription.is_active())

    def test_subscription_string_representation(self):
        """Test subscription string representation"""
        user = CustomUser.objects.create_user(
            email='string@example.com',
            full_name='String User',
            user_type='landlord',
            password='testpass123'
        )
        subscription = user.subscription
        self.assertEqual(str(subscription), f"{user.email} - {subscription.plan}")


class SubscriptionViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        # Don't create subscription manually - it's auto-created
        self.client.force_authenticate(user=self.landlord)

    def test_subscription_status_view(self):
        """Test subscription status endpoint"""
        response = self.client.get(reverse('subscription-status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('plan', response.data)
        self.assertIn('is_active', response.data)

    def test_property_creation_with_subscription(self):
        """Test property creation respects subscription limits"""
        property_data = {
            'name': 'Test Property',
            'city': 'Nairobi',
            'state': 'Nairobi County',
            'unit_count': 5
        }
        response = self.client.post(reverse('property-create'), property_data)
        
        # Should succeed with free plan (2 property limit)
        if self.landlord.subscription.plan == 'free':
            # First property should succeed
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # Try to create second property
            property_data2 = {
                'name': 'Second Property',
                'city': 'Nairobi',
                'state': 'Nairobi County',
                'unit_count': 3
            }
            response2 = self.client.post(reverse('property-create'), property_data2)
            self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
            
            # Third property should fail for free plan
            property_data3 = {
                'name': 'Third Property',
                'city': 'Nairobi',
                'state': 'Nairobi County',
                'unit_count': 2
            }
            response3 = self.client.post(reverse('property-create'), property_data3)
            # Should be 403 Forbidden due to subscription limit
            self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)
