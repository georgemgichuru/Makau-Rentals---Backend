from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # from accounts/urls.py
    path('api/accounts/', include('accounts.urls')),
    # from payments/urls.py
    path("api/payments/", include("payments.urls")),
    # from communication/urls.py
    path("api/communication/", include("communication.urls")),
]
