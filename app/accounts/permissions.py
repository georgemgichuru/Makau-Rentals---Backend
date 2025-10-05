from rest_framework.permissions import BasePermission
from django.http import HttpResponse
from .models import Subscription, Unit

# Decorator to check if user is a superuser
class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

# Decorator to check if user is a landlord
class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'landlord'

# Decorator to check if user is a tenant
class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'tenant'

# Permission to check if landlord has an active subscription
class HasActiveSubscription(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.user_type == 'landlord':
            subscription = Subscription.objects.filter(user=request.user).first()
            return subscription and subscription.is_active()
        elif request.user.user_type == 'tenant':
            # Check if tenant's landlord has active subscription
            units = Unit.objects.filter(tenant=request.user)
            if units.exists():
                landlord = units.first().property.landlord
                subscription = Subscription.objects.filter(user=landlord).first()
                return subscription and subscription.is_active()
            return False
        return False

# Decorator to check if landlord has an active subscription
def require_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse("Authentication required.")
        landlord = request.user
        subscription = Subscription.objects.filter(user=landlord).first()
        if subscription and subscription.is_active:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse("You are not subscribed to the service. Please subscribe to access this view.")
    return wrapper

# Decorator to check if tenant's landlord has an active subscription
def require_tenant_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse("Authentication required.")
        if request.user.user_type == 'tenant':
            # Find tenant's unit and landlord
            from .models import Unit
            units = Unit.objects.filter(tenant=request.user)
            if units.exists():
                landlord = units.first().property.landlord
                subscription = Subscription.objects.filter(user=landlord).first()
                if subscription and subscription.is_active:
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponse("Your landlord's subscription is inactive. Please contact your landlord.")
            else:
                return HttpResponse("No unit assigned to you.")
        else:
            return view_func(request, *args, **kwargs)  # For non-tenants, allow
    return wrapper
