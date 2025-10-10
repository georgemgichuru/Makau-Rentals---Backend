import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

# Delete existing user
try:
    user = CustomUser.objects.get(email='test@example.com')
    user.delete()
    print("Deleted existing user")
except CustomUser.DoesNotExist:
    print("User not found")

# Create new user
user = CustomUser.objects.create_user(
    email='test@example.com',
    full_name='Test User',
    user_type='tenant',
    password='testpass123'
)
print("Created new user: test@example.com / testpass123")
