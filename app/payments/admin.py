from django.contrib import admin
from .models import Payment, SubscriptionPayment

admin.site.register(Payment)
admin.site.register(SubscriptionPayment)

# Register your models here.
