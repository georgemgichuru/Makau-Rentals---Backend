from rest_framework.permissions import BasePermission

class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'landlord'

class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'tenant'
    

from django.http import HttpResponseForbidden

# To protect views that require an active subscription
def active_landlord_subscription_required(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.user_type != 'landlord' or not user.has_active_subscription():
            return HttpResponseForbidden("Subscription required or expired.")
        return view_func(request, *args, **kwargs)
    return wrapper

