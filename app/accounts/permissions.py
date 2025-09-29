from rest_framework.permissions import BasePermission
from django.http import HttpResponse
from .models import Subscription

# Decorator to check if user is a landlord
class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'landlord'
# Decorator to check if user is a tenant
class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'tenant'

# Decorator to check if landlord has an active subscription
def require_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        landlord = request.user
        subscription = Subscription.objects.filter(user=landlord).first()
        if subscription and subscription.is_active:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse("You are not subscribed to the service. Please subscribe to access this view.")
    return wrapper
