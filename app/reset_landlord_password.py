import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

try:
    user = CustomUser.objects.get(email='landlord@example.com')
    user.set_password('landlord123')
    user.save()
    print(f"Password reset for landlord user: {user.email}")
    print(f"User type: {user.user_type}")
    print(f"Is active: {user.is_active}")
except CustomUser.DoesNotExist:
    print("Landlord user not found")
