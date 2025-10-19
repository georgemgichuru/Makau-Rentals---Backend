from django.db import models
from accounts.models import CustomUser, Unit, Subscription
from datetime import timedelta
from django.core.exceptions import ValidationError
import uuid

# Add validation and better field definitions
class Payment(models.Model):
    PAYMENT_TYPES = [
        ('rent', 'Rent'),
        ('deposit', 'Deposit'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Make tenant and unit required for rent payments
    tenant = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'tenant'},
        related_name='payments'
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='payments')
    
    # Add more fields for better tracking
    reference_number = models.CharField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, default='mpesa', choices=[
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
    ])
        # Add this field to track M-Pesa checkout requests
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    # Add created and updated timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.payment_type == 'rent' and not self.unit:
            raise ValidationError("Rent payments must be associated with a unit")
            
    def save(self, *args, **kwargs):
        # Generate reference number if not set
        if not self.reference_number:
            self.reference_number = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class SubscriptionPayment(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt_number = models.CharField(
        max_length=50,
        blank=True,  # Allow empty strings
        null=True,
        default=""
    )
    transaction_date = models.DateTimeField(auto_now_add=True)
    subscription_type = models.CharField(max_length=20, choices=Subscription.PLAN_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Success", "Success"), ("Failed", "Failed")],
        default="Pending"
    )

    class Meta:
        # Simple unique constraint for non-empty receipt numbers
        constraints = [
            models.UniqueConstraint(
                fields=['mpesa_receipt_number'],
                name='unique_mpesa_receipt',
                condition=~models.Q(mpesa_receipt_number='')
            )
        ]

    def __str__(self):
        return f"Subscription Payment {self.id} - {self.subscription_type}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def _get_plan_duration(self):
        durations = {
            "free": timedelta(days=60),
            "starter": timedelta(days=30),
            "basic": timedelta(days=30),
            "professional": timedelta(days=30),
            # "onetime" will be treated as lifetime (None) by the subscription logic
        }
        return durations.get(self.subscription_type, timedelta(days=30))
