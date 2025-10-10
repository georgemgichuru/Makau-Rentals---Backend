from django.utils import timezone
from accounts.models import CustomUser, Property, UnitType, Unit
from communication.models import Report

# Get landlord
landlord = CustomUser.objects.filter(user_type='landlord').first()
if not landlord:
    print("No landlord found. Skipping test data creation.")
else:
    print("Landlord found")
    
    # Create Property
    property_obj = Property.objects.create(
        landlord=landlord,
        name='Test Property',
        city='Nairobi',
        state='Kenya',
        unit_count=5
    )
    print(f"Created Property: {property_obj.id}")
    
    # Create UnitType
    unit_type = UnitType.objects.create(
        landlord=landlord,
        name='1 Bedroom',
        deposit=1000,
        rent=5000
    )
    print(f"Created UnitType: {unit_type.id}")
    
    # Create Unit
    unit = Unit.objects.create(
        property_obj=property_obj,
        unit_number='101',
        floor=1,
        bedrooms=1,
        bathrooms=1,
        unit_type=unit_type,
        rent=5000,
        deposit=1000
    )
    print(f"Created Unit: {unit.id}")
    
    # Get tenant and assign to unit
    tenant = CustomUser.objects.filter(user_type='tenant').first()
    if tenant:
        unit.tenant = tenant
        unit.save()
        print(f"Assigned tenant {tenant.id} to unit {unit.id}")
        
        # Create Report
        report = Report.objects.create(
            tenant=tenant,
            unit=unit,
            issue_category='maintenance',
            priority_level='medium',
            issue_title='Test Issue',
            description='Test description'
        )
        print(f"Created Report: {report.id}")
    else:
        print("No tenant found. Skipping report creation.")
