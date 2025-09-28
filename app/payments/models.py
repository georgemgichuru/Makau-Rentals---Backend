from django.db import models
from accounts.models import CustomUser, Unit, Subscription
from datetime import timedelta

class Payment(models.Model):
    tenant = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'tenant'},
        related_name='rent_payments'
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Success", "Success"), ("Failed", "Failed")],
        default="Pending"
    )

    def __str__(self):
        return f"{self.tenant.email} - Unit {self.unit.unit_number} - KES {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update unit rent tracking if payment is successful
        if self.status == "Success":
            self.unit.rent_paid += self.amount
            self.unit.rent_remaining = max(self.unit.rent - self.unit.rent_paid, 0)
            self.unit.save()


class SubscriptionPayment(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'landlord'},
        related_name='subscription_payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt_number = models.CharField(max_length=100, unique=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    subscription_type = models.CharField(
        max_length=20,
        choices=Subscription.PLAN_CHOICES
    )

    def __str__(self):
        return f"{self.user.email} - {self.subscription_type} - {self.mpesa_receipt_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update user's subscription if payment is successful
        subscription, created = Subscription.objects.get_or_create(user=self.user)
        subscription.plan = self.subscription_type
        subscription.start_date = self.transaction_date
        subscription.expiry_date = self.transaction_date + self._get_plan_duration()
        subscription.save()

    def _get_plan_duration(self):
        durations = {
            "free": timedelta(days=60),
            "basic": timedelta(days=30),
            "medium": timedelta(days=90),
            "premium": timedelta(days=365),
        }
        return durations.get(self.subscription_type, timedelta(days=30))
