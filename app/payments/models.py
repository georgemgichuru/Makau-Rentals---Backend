from django.db import models
from accounts.models import CustomUser, Unit 

class Payment(models.Model):
    tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'tenant'})
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Success", "Success"), ("Failed", "Failed")],
        default="Pending"
    )

    def __str__(self):
        return f"{self.tenant.email} - {self.unit.unit_number} - {self.amount} ({self.status})"
