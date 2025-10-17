from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch

from .models import Report
from accounts.models import Property, Unit, UnitType

CustomUser = get_user_model()

class ReportModelTests(TestCase):
    def setUp(self):
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        
        self.tenant = CustomUser.objects.create_user(
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
            rent=15000,
            deposit=5000,
            tenant=self.tenant,
            is_available=False
        )

    def test_report_creation(self):
        """Test creating a maintenance report"""
        report = Report.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            issue_category='plumbing',
            priority_level='medium',
            issue_title='Leaking faucet',
            description='Kitchen faucet is leaking'
        )
        self.assertEqual(report.issue_title, 'Leaking faucet')
        self.assertEqual(report.status, 'open')

    def test_report_default_status(self):
        """Test that report status defaults to 'open'"""
        report = Report.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            issue_category='electrical',
            priority_level='high',
            issue_title='Power outage',
            description='No power in unit'
        )
        self.assertEqual(report.status, 'open')

    def test_report_string_representation(self):
        """Test report string representation"""
        report = Report.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            issue_category='plumbing',
            priority_level='medium',
            issue_title='Leaking faucet',
            description='Kitchen faucet is leaking'
        )
        expected_str = f"Report by {self.tenant.full_name} - Leaking faucet"
        self.assertEqual(str(report), expected_str)


class ReportViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.landlord = CustomUser.objects.create_user(
            email='landlord@test.com',
            full_name='Test Landlord',
            user_type='landlord',
            password='testpass123'
        )
        
        self.tenant = CustomUser.objects.create_user(
            email='tenant@test.com',
            full_name='Test Tenant',
            user_type='tenant',
            password='testpass123'
        )
        
        self.other_tenant = CustomUser.objects.create_user(
            email='other@test.com',
            full_name='Other Tenant',
            user_type='tenant',
            password='testpass123'
        )
        
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
            tenant=self.tenant,
            is_available=False
        )
        
        self.other_unit = Unit.objects.create(
            property_obj=self.property,
            unit_type=self.unit_type,
            unit_number='102',
            unit_code='U-102',
            rent=15000,
            deposit=5000,
            tenant=self.other_tenant,
            is_available=False
        )
        
        self.report = Report.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            issue_category='plumbing',
            priority_level='medium',
            issue_title='Leaking faucet',
            description='Kitchen faucet is leaking'
        )

    def test_create_report_tenant(self):
        """Test tenant can create a report"""
        self.client.force_authenticate(user=self.tenant)
        report_data = {
            'unit': self.unit.id,
            'issue_category': 'electrical',
            'priority_level': 'high',
            'issue_title': 'Power outage',
            'description': 'No electricity in living room'
        }
        response = self.client.post(reverse('create-report'), report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_open_reports_view_tenant(self):
        """Test tenant can view their open reports"""
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(reverse('open-reports'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_open_reports_view_landlord(self):
        """Test landlord can view open reports for their properties"""
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get(reverse('open-reports'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_urgent_reports_view(self):
        """Test urgent reports view"""
        # Create an urgent report
        Report.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            issue_category='safety/violence',
            priority_level='urgent',
            issue_title='Security issue',
            description='Broken lock on main door'
        )
        
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(reverse('urgent-reports'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_in_progress_reports_view(self):
        """Test in-progress reports view"""
        # Update report to in-progress
        self.report.status = 'in_progress'
        self.report.save()
        
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(reverse('in-progress-reports'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_resolved_reports_view(self):
        """Test resolved reports view"""
        # Update report to resolved
        self.report.status = 'resolved'
        self.report.save()
        
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(reverse('resolved-reports'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_report_status_landlord(self):
        """Test landlord can update report status"""
        self.client.force_authenticate(user=self.landlord)
        update_data = {'status': 'in_progress'}
        response = self.client.patch(
            reverse('update-report-status', args=[self.report.id]),
            update_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')

    def test_tenant_cannot_update_other_reports(self):
        """Test tenant cannot update reports they don't own"""
        # Create a report for other tenant
        other_report = Report.objects.create(
            tenant=self.other_tenant,
            unit=self.other_unit,
            issue_category='plumbing',
            priority_level='medium',
            issue_title='Other report',
            description='Other tenant report'
        )
        
        self.client.force_authenticate(user=self.tenant)
        update_data = {'status': 'resolved'}
        response = self.client.patch(
            reverse('update-report-status', args=[other_report.id]),
            update_data
        )
        # Should return 404 or 403, not 200
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    @patch('communication.views.send_landlord_email')
    def test_send_email_to_tenants(self, mock_send_email):
        """Test landlord can send emails to tenants"""
        self.client.force_authenticate(user=self.landlord)
        email_data = {
            'subject': 'Test Email',
            'message': 'This is a test email',
            'send_to_all': True
        }
        response = self.client.post(reverse('send-email'), email_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()
