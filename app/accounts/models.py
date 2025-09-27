from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    date_joined = models.DateTimeField(auto_now_add=True)
    type = [('landlord', 'Landlord'), ('tenant', 'Tenant')]
    user_type = models.CharField(max_length=10, choices=type)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email and self.user_type and self.first_name and self.last_name
    
class Property(models.Model):
    landlord = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    units = models.IntegerField()

    def __str__(self):
        return f" {self.name}, {self.landlord}, {self.city}"
    
class Unit(models.Model):
    property = models.ForeignKey(property, on_delete=models.CASCADE)
    unit_number = models.CharField(max_length=10)
    floor = models.IntegerField()
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    # Define the rent amount for the unit 
    # This field represents the total rent amount for the unit and is not nullable.
    # Only Landlords can set this field.
    rent = models.DecimalField(max_digits=10, decimal_places=2)
    tenant = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    # Track rent paid and remaining amounts
    # These fields help in managing the rent payments for the unit.
    # Rent paid is the amount already paid by the tenant, while rent remaining is the outstanding amount.
    rent_paid = models.DecimalField(max_digits=10, decimal_places=2)
    rent_remaining = models.DecimalField(max_digits=10, decimal_places=2)
    # Deposit is the amount for booking the unit and is required at the time of booking.
    deposit = models.DecimalField(max_digits=10, decimal_places=2)
    # Availability status of the unit
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"