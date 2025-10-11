# permissions_fixed.py
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .models import Subscription, Unit

class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "landlord"

class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "tenant"

class HasActiveSubscription(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.user_type == "landlord":
            subscription = Subscription.objects.filter(user=request.user).first()
            return subscription and subscription.is_active()
        elif request.user.user_type == "tenant":
            units = Unit.objects.filter(tenant=request.user)
            if units.exists():
                landlord = units.first().property_obj.landlord
                subscription = Subscription.objects.filter(user=landlord).first()
                return subscription and subscription.is_active()
            return False
        return False

def require_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        landlord = request.user
        subscription = Subscription.objects.filter(user=landlord).first()
        if subscription and subscription.is_active():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied("You are not subscribed to the service. Please subscribe to access this view.")
    return wrapper

def require_tenant_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        if request.user.user_type == "tenant":
            from .models import Unit
            units = Unit.objects.filter(tenant=request.user)
            if units.exists():
                landlord = units.first().property_obj.landlord
                subscription = Subscription.objects.filter(user=landlord).first()
                if subscription and subscription.is_active():
                    return view_func(request, *args, **kwargs)
                else:
                    raise PermissionDenied("Your landlord's subscription is inactive. Please contact your landlord.")
            else:
                raise PermissionDenied("No unit assigned to you.")
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

class CanAccessReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.user_type == "tenant":
            return obj.tenant == request.user
        elif request.user.user_type == "landlord":
            return obj.unit.property_obj.landlord == request.user
        return False