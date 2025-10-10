import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

# Create a test landlord user
user, created = CustomUser.objects.get_or_create(
    email='landlord@example.com',
    defaults={
        'full_name': 'Test Landlord',
        'user_type': 'landlord',
        'password': 'landlord123'
    }
)

if created:
    user.set_password('landlord123')
    user.save()
    print("Landlord user created: landlord@example.com / landlord123")
else:
    print("Landlord user already exists: landlord@example.com")
