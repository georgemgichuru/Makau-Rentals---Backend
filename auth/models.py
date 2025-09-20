# For custom user model
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
# universal unique identifier
import uuid
# Auth User models for Signup, Login Authentication and authorization systems


# Global User model with common meta-data for the Tenant and Landlord Properties
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    government_id = models.CharField(max_length=50, unique=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    tenant = models.BooleanField(default=False)
    landlord = models.BooleanField(default=False)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']


