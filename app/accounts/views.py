from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from accounts.serializers import (
    PropertySerializer,
    UnitSerializer,
    UserSerializer,
    PasswordResetSerializer,
)
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import Property, Unit, CustomUser, Subscription
from .permissions import IsLandlord, IsTenant, require_subscription

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# accounts/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# Lists a single user (cached)
# View to get user details
@method_decorator(require_subscription, name='dispatch')
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        cache_key = f"user:{user_id}"
        user_data = cache.get(cache_key)

        if not user_data:
            try:
                user = CustomUser.objects.get(id=user_id)
                serializer = UserSerializer(user)
                user_data = serializer.data
                cache.set(cache_key, user_data, timeout=300)  # cache for 5 minutes
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found"}, status=404)

        return Response(user_data)


# Lists all tenants (cached)
# View to list all tenants (landlord only)
@method_decorator(require_subscription, name='dispatch')
class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def get(self, request):
        cache_key = "tenants:list"
        tenants_data = cache.get(cache_key)

        if not tenants_data:
            tenants = CustomUser.objects.filter(user_type="tenant")
            serializer = UserSerializer(tenants, many=True)
            tenants_data = serializer.data
            cache.set(cache_key, tenants_data, timeout=300)

        return Response(tenants_data)


# Create a new user (invalidate cache)
# View to create a new user Landlord or Tenant
class UserCreateView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Invalidate tenant list cache if a tenant was created
            if user.user_type == "tenant":
                cache.delete("tenants:list")
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# Create a new property (invalidate landlord cache)
# View to create a new property (landlord only) 
PLAN_LIMITS = {
    "free": 2,      # trial landlords can only create 2 properties
    "basic": 2,
    "medium": 5,
    "premium": 10,
}
@method_decorator(require_subscription, name='dispatch')
class CreatePropertyView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def post(self, request):
        user = request.user

        # Fetch subscription
        try:
            subscription = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return Response({"error": "No active subscription found."}, status=403)

        plan = subscription.plan.lower()

        # Check if subscription is active
        if not subscription.is_active():
            return Response({"error": "Your subscription has expired. Please renew or upgrade."}, status=403)

        # Get plan limit
        max_properties = PLAN_LIMITS.get(plan)
        if max_properties is None:
            return Response({"error": f"Unknown plan type: {plan}"}, status=400)

        # Count current properties
        current_count = Property.objects.filter(landlord=user).count()
        if current_count >= max_properties:
            return Response({
                "error": f"Your current plan ({plan}) allows a maximum of {max_properties} properties. Upgrade to add more."
            }, status=403)

        # Proceed with creation
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            property = serializer.save(landlord=user)
            cache.delete(f"landlord:{user.id}:properties")  # clear cache if you're caching landlord properties
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# List landlord properties (cached)
# View to list all properties of a landlord (landlord only)
@method_decorator(require_subscription, name='dispatch')
class LandlordPropertiesView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def get(self, request):
        cache_key = f"landlord:{request.user.id}:properties"
        properties_data = cache.get(cache_key)

        if not properties_data:
            properties = Property.objects.filter(landlord=request.user)
            serializer = PropertySerializer(properties, many=True)
            properties_data = serializer.data
            cache.set(cache_key, properties_data, timeout=300)

        return Response(properties_data)


# Create a new unit (invalidate landlord cache)
# View to create a new unit in a property (landlord only)
@method_decorator(require_subscription, name='dispatch')

class CreateUnitView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def post(self, request):
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.save()
            cache.delete(f"landlord:{request.user.id}:properties")
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# List units of a property (cached)
# View to list all units of a property (landlord only)
@method_decorator(require_subscription, name='dispatch')

class PropertyUnitsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def get(self, request, property_id):
        cache_key = f"property:{property_id}:units"
        units_data = cache.get(cache_key)

        if not units_data:
            try:
                property = Property.objects.get(id=property_id, landlord=request.user)
                units = Unit.objects.filter(property=property)
                serializer = UnitSerializer(units, many=True)
                units_data = serializer.data
                cache.set(cache_key, units_data, timeout=300)
            except Property.DoesNotExist:
                return Response(
                    {"error": "Property not found or you do not have permission"},
                    status=404,
                )

        return Response(units_data)


# Assign tenant to unit (invalidate cache)
# View to assign a tenant to a unit (tenant only)
class AssignTenantToUnitView(APIView):
    permission_classes = [IsAuthenticated, IsTenant]

    def post(self, request, unit_id, tenant_id):
        try:
            unit = Unit.objects.get(id=unit_id)
            tenant = CustomUser.objects.get(id=tenant_id, user_type="tenant")
            unit.tenant = tenant
            unit.is_available = False
            unit.save()
            # Invalidate property units cache
            cache.delete(f"property:{unit.property.id}:units")
            return Response({"message": "Tenant assigned to unit successfully"})
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found"}, status=404)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Tenant not found or invalid user type"}, status=404
            )


# Password reset (no caching needed)
# view for password reset
class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password reset email sent."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# View to update the Property details (landlord only) and Unit details (landlord only) and delete
@method_decorator(require_subscription, name='dispatch')

class UpdatePropertyView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def put(self, request, property_id):
        try:
            property = Property.objects.get(id=property_id, landlord=request.user)
            serializer = PropertySerializer(property, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"landlord:{request.user.id}:properties")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Property.DoesNotExist:
            return Response({"error": "Property not found or you do not have permission"}, status=404)

    def delete(self, request, property_id):
        try:
            property = Property.objects.get(id=property_id, landlord=request.user)
            property.delete()
            cache.delete(f"landlord:{request.user.id}:properties")
            return Response({"message": "Property deleted successfully."}, status=200)
        except Property.DoesNotExist:
            return Response({"error": "Property not found or you do not have permission"}, status=404)
@method_decorator(require_subscription, name='dispatch')
class UpdateUnitView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def put(self, request, unit_id):
        try:
            unit = Unit.objects.get(id=unit_id, property__landlord=request.user)
            serializer = UnitSerializer(unit, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"landlord:{request.user.id}:properties")
                cache.delete(f"property:{unit.property.id}:units")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found or you do not have permission"}, status=404)

    def delete(self, request, unit_id):
        try:
            unit = Unit.objects.get(id=unit_id, property__landlord=request.user)
            property_id = unit.property.id
            unit.delete()
            cache.delete(f"landlord:{request.user.id}:properties")
            cache.delete(f"property:{property_id}:units")
            return Response({"message": "Unit deleted successfully."}, status=200)
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found or you do not have permission"}, status=404)

# view to update user details (landlord and tenant) and to delete the user account (landlord and tenant)
@method_decorator(require_subscription, name='dispatch')
class UpdateUserView(APIView):  
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        if request.user.id != user_id:
            return Response({"error": "You do not have permission to update this user."}, status=403)
        try:
            user = CustomUser.objects.get(id=user_id)
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"user:{user_id}")
                if user.user_type == "tenant":
                    cache.delete("tenants:list")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

    def delete(self, request, user_id):
        if request.user.id != user_id:
            return Response({"error": "You do not have permission to delete this user."}, status=403)
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            cache.delete(f"user:{user_id}")
            if user.user_type == "tenant":
                cache.delete("tenants:list")
            return Response({"message": "User deleted successfully."}, status=200)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
# TODO: Add url routes for the new views in urls.py, Update user view, Update property view, Update unit view, Assign tenant to unit view, Property units view

# View to check subscription status (landlord only)
@login_required
def subscription_status(request):
    landlord = request.user
    subscription = Subscription.objects.filter(user=landlord).first()
    if subscription:
        status = 'Subscribed' if subscription.is_active else 'Inactive'
        return HttpResponse(f"Subscription Status: {status}")
    else:
        return HttpResponse("No subscription found")