from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    # ensure the email is normalized and user_type is provided
    def create_user(self, email, first_name, last_name, user_type, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not user_type:
            raise ValueError("User type must be set (landlord or tenant)")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)

        # Auto-assign free trial for landlords
        if user_type == "landlord":
            Subscription.objects.create(
                user=user,
                plan="free",
                expiry_date=timezone.now() + timedelta(days=60)
            )

        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # set default user_type if not provided
        user_type = extra_fields.pop("user_type", "landlord")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
            password=password,
            **extra_fields
        )


class CustomUser(AbstractBaseUser):
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
    objects = CustomUserManager()

    # Check if user has an active subscription
    def has_active_subscription(self):
        if hasattr(self, "subscription"):
            return self.subscription.is_active()
        return False

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Subscription(models.Model):
    PLAN_CHOICES = [
        ("free", "Free (60-day trial)"),
        ("basic", "Basic"),
        ("medium", "Medium"),
        ("premium", "Premium"),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-assign expiry for free plan
        if self.plan == "free" and not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=60)
        super().save(*args, **kwargs)

    # Check if subscription is still valid
    def is_active(self):
        return self.expiry_date is None or self.expiry_date > timezone.now()

    def __str__(self):
        return f"{self.user.email} - {self.plan}"


class Property(models.Model):
    landlord = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    units = models.IntegerField()

    def __str__(self):
        return f"{self.name}, {self.city}"


class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
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

    @property
    def balance(self):
        return self.rent_remaining - self.rent_paid

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"


# REMINDER: payments is shown in the Unit model as rent_paid and rent_remaining
# TODO: Protect the subscription features using a decorator or middleware to ensure only subscribed users can access them
# TODO: Ensure payments for subscription and rent are two different things
