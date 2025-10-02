from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # from accounts/urls.py
    path('api/accounts/', include('accounts.urls')),
    # from payments/urls.py
    path("api/payments/", include("payments.urls")),
    # from communication/urls.py
    #TODO: Uncomment when ready to use communication app AFTER FIXING IT
    path("api/communication/", include("communication.urls")),
]
