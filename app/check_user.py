import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

try:
    user = CustomUser.objects.get(email='test@example.com')
    print(f"User found: {user.email}")
    print(f"Full name: {user.full_name}")
    print(f"User type: {user.user_type}")
    print(f"Is active: {user.is_active}")
    print(f"Password hash: {user.password[:20]}...")
except CustomUser.DoesNotExist:
    print("User not found")
