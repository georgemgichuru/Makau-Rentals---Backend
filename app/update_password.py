import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import CustomUser

try:
    user = CustomUser.objects.get(email='test@example.com')
    user.set_password('testpass123')
    user.save()
    print("Password updated for test@example.com")
except CustomUser.DoesNotExist:
    print("User not found")
