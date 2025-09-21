from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth', include('auth.urls')),
    path('api/comms', include('communication.urls')),
    path('api/payments', include('payments.urls')),
    path('api/property', include('properties.urls'))
]
