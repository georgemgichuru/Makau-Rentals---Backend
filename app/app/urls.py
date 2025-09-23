from django.contrib import admin
from django.urls import path, include

""" path('api/comms', include('communication.urls')),
    path('api/payments', include('payments.urls')),"""
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
]
