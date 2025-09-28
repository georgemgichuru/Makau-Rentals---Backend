from django.contrib import admin
from django.urls import path, include

""" path('api/comms', include('communication.urls')),
    path('api/payments', include('payments.urls')),"""
urlpatterns = [
    path('admin/', admin.site.urls),
    # from accounts/urls.py
    path('api/accounts/', include('accounts.urls')),
    # from payments/urls.py
    path("api/payments/", include("payments.urls")),
]
