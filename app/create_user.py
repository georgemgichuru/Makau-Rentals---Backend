import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

# Create a test user
user, created = CustomUser.objects.get_or_create(
    email='test@example.com',
    defaults={
        'full_name': 'Test User',
        'user_type': 'tenant',
        'password': 'testpass123'
    }
)

if created:
    user.set_password('testpass123')
    user.save()
    print("User created: test@example.com / testpass123")
else:
    print("User already exists: test@example.com")
