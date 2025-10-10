from django.contrib import admin
from .models import CustomUser, UnitType

# Register your models here
admin.site.register(CustomUser)
admin.site.register(UnitType)
