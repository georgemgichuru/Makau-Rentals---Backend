from rest_framework import permissions
from django.core.cache import cache
from accounts.models import CustomUser, Subscription

class IsTenantWithUnit(permissions.BasePermission):
    """
    Allows access only to tenants who have at least one assigned unit.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.user_type != 'tenant':
            return False
        
        # Check cache first
        cache_key = f"tenant_has_unit:{request.user.id}"
        has_unit = cache.get(cache_key)
        
        if has_unit is None:
            # Check if tenant has any units assigned (OneToOneField so use hasattr)
            has_unit = hasattr(request.user, 'unit') and request.user.unit is not None
            cache.set(cache_key, has_unit, timeout=300)  # Cache for 5 minutes
        
        return has_unit

class IsLandlordWithActiveSubscription(permissions.BasePermission):
    """
    Allows access only to landlords with active subscriptions.
    """
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
