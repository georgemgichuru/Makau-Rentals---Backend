from django.db import models
from accounts.models import CustomUser, Unit, Subscription
from datetime import timedelta

class Payment(models.Model):
    PAYMENT_TYPES = [
        ('rent', 'Rent'),
        ('deposit', 'Deposit'),
    ]
    tenant = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'tenant'},
        related_name='payments',
        null=True,
        blank=True
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    unit_type = models.ForeignKey('accounts.UnitType', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES, default='rent')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Success", "Success"), ("Failed", "Failed")],
        default="Pending"
    )

    def __str__(self):
        unit_str = f"Unit {self.unit.unit_number}" if self.unit else "Deposit"
        return f"{self.tenant.email} - {unit_str} - KES {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
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
        # Remove or modify the unique constraint to allow empty strings
        constraints = [
            models.UniqueConstraint(
                fields=['mpesa_receipt_number'],
                name='unique_mpesa_receipt',
                condition=~models.Q(mpesa_receipt_number='')  # Only enforce uniqueness for non-empty values
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
