# accounts/permissions.py - FIXED VERSION
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
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
                # FIXED: Use property_obj instead of property
                landlord = units.first().property_obj.landlord
                subscription = Subscription.objects.filter(user=landlord).first()
                return subscription and subscription.is_active()
            return False
        return False

# Decorator to check if landlord has an active subscription
def require_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        landlord = request.user
        subscription = Subscription.objects.filter(user=landlord).first()
        # FIXED: Call is_active() as a method
        if subscription and subscription.is_active():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied("You are not subscribed to the service. Please subscribe to access this view.")
    return wrapper

# Decorator to check if tenant's landlord has an active subscription


# Permission to access reports: tenants can access their own, landlords can access reports on their properties
class CanAccessReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.user_type == 'tenant':
            return obj.tenant == request.user
        elif request.user.user_type == 'landlord':
            # FIXED: Use property_obj instead of property
            return obj.unit.property_obj.landlord == request.user
        return False