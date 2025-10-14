from rest_framework import permissions
from django.core.cache import cache
from .models import CustomUser, Subscription
# REMOVE the problematic Payment import - it causes circular dependency

class IsLandlord(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'landlord'

class IsTenant(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'tenant'

class IsSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

class HasActiveSubscription(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.user_type != 'landlord':
            return False
        
        # Use cache to avoid repeated database queries
        cache_key = f"subscription_status:{request.user.id}"
        has_active_sub = cache.get(cache_key)
        
        if has_active_sub is None:
            try:
                subscription = Subscription.objects.get(user=request.user)
                has_active_sub = subscription.is_active()
            except Subscription.DoesNotExist:
                has_active_sub = False
            cache.set(cache_key, has_active_sub, timeout=300)  # Cache for 5 minutes
        
        return has_active_sub

# Remove the problematic IsTenantWithActivePayment permission if it exists
# as it causes circular imports with Payment model

class CanAccessReport(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.user_type == 'tenant':
            return obj.tenant == request.user
        elif request.user.user_type == 'landlord':
            return obj.unit.property_obj.landlord == request.user
        return False
