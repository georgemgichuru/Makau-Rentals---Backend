from django.contrib import admin
from .models import CustomUser, UnitType,Property, Unit, Subscription

# Register your models here
admin.site.register(CustomUser)
admin.site.register(Unit)
admin.site.register(Subscription)
admin.site.register(UnitType)
admin.site.register(Property)
