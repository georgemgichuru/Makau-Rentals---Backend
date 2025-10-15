from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import CustomUser, Property, Unit, UnitType, Subscription
from payments.models import Payment

class UnitTypeAndUnitCreationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a landlord user
        self.landlord = CustomUser.objects.create_user(email='landlord@test.com', full_name='Landlord One', user_type='landlord', password='testpass')
        # ensure subscription exists
        Subscription.objects.create(user=self.landlord, plan='basic')
        # Authenticate client as landlord where needed
        self.client.force_authenticate(user=self.landlord)

    def test_cannot_create_unit_without_unittype(self):
        # Create a property first
        prop = Property.objects.create(landlord=self.landlord, name='P1', city='Nairobi', state='Nairobi', unit_count=1)
        # Try to create a unit via API
        url = reverse('create-unit')
        data = {
            'property_obj': prop.id,
            'unit_number': '1',
            'floor': 1,
            'bedrooms': 1,
            'bathrooms': 1,
            'rent': '1000.00',
            'deposit': '500.00'
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Landlord must create at least one UnitType', str(resp.data))

    def test_create_unittype_and_then_unit(self):
        # Create a UnitType via API
        url_ut = reverse('unittype-list-create')
        data_ut = {'name': 'single', 'deposit': '500', 'rent': '2000'}
        resp_ut = self.client.post(url_ut, data_ut, format='json')
        self.assertEqual(resp_ut.status_code, 201)
        ut_id = resp_ut.data['id']

        # Create a property
        prop = Property.objects.create(landlord=self.landlord, name='P2', city='Nairobi', state='Nairobi', unit_count=1)

        # Now create a unit referencing the unit_type
        url = reverse('create-unit')
        data = {
            'property_obj': prop.id,
            'unit_number': '1',
            'unit_type': ut_id,
            'floor': 1,
            'bedrooms': 1,
            'bathrooms': 1,
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('unit_code', resp.data)
        unit = Unit.objects.get(id=resp.data['id'])
        self.assertEqual(unit.unit_type.id, ut_id)

class TenantSignupAssignTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create landlord and unit type and property + unit
        self.landlord = CustomUser.objects.create_user(email='landlord2@test.com', full_name='Landlord Two', user_type='landlord', password='testpass')
        Subscription.objects.create(user=self.landlord, plan='basic')
        self.ut = UnitType.objects.create(landlord=self.landlord, name='one_bed', deposit='100', rent='1000')
        self.prop = Property.objects.create(landlord=self.landlord, name='P3', city='Nairobi', state='Nairobi', unit_count=1)
        self.unit = Unit.objects.create(property_obj=self.prop, unit_code='U-1-1', unit_number='1', unit_type=self.ut, is_available=True, rent=self.ut.rent, deposit=self.ut.deposit)

    def test_tenant_signup_assign_after_deposit(self):
        # Create tenant
        resp = self.client.post(reverse('signup'), data={'email':'tenant@test.com','full_name':'Tenant One','password':'tpass','user_type':'tenant','landlord_code':self.landlord.landlord_code,'unit_code':self.unit.unit_code}, format='json')
        self.assertEqual(resp.status_code, 201)
        tenant = CustomUser.objects.get(email='tenant@test.com')
        # No deposit payments yet; unit should still be unassigned
        self.unit.refresh_from_db()
        self.assertIsNone(self.unit.tenant)
        # Add a deposit payment for this tenant
        Payment.objects.create(tenant=tenant, unit=self.unit, amount=self.unit.deposit, payment_type='deposit', status='Success')

        # Simulate assignment by calling AssignTenantToUnitView directly via APIRequestFactory
        from rest_framework.test import APIRequestFactory
        from .views import AssignTenantView
        factory = APIRequestFactory()
        request = factory.post('/')
        # attach user to request and authenticate as landlord
        request.user = self.landlord
        view = AssignTenantView.as_view()
        resp = view(request, unit_id=self.unit.id, tenant_id=tenant.id)
        # Refresh unit and assert assigned
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.tenant.id, tenant.id)
