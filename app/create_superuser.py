import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

# Create a superuser
superuser, created = CustomUser.objects.get_or_create(
    email='admin@example.com',
    defaults={
        'full_name': 'Admin User',
        'user_type': 'landlord',
        'is_staff': True,
        'is_superuser': True,
    }
)

if created:
    superuser.set_password('adminpass123')
    superuser.save()
    print("Superuser created: admin@example.com / adminpass123")
else:
    print("Superuser already exists: admin@example.com")
