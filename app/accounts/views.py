from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from accounts.serializers import (
    PropertySerializer,
    UnitSerializer,
    UnitNumberSerializer,
    UserSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    ReminderPreferencesSerializer,
    AvailableUnitsSerializer,
)
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import Property, Unit, CustomUser, Subscription, UnitType
from payments.models import Payment
from .permissions import IsLandlord, IsTenant, IsSuperuser, HasActiveSubscription
from communication.models import Report
from communication.serializers import ReportSerializer
from django.core.exceptions import ValidationError

import logging

import uuid

logger = logging.getLogger(__name__)

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# accounts/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer
from .serializers import UnitTypeSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class UnitTypeListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        unit_types = request.user.unit_types.all()
        serializer = UnitTypeSerializer(unit_types, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UnitTypeSerializer(data=request.data)
        if serializer.is_valid():
            unit_type = serializer.save(landlord=request.user)

            # Automatically create units based on the unit_count
            unit_count = int(request.data.get('unit_count', 1))
            property_id = request.data.get('property_id')
            
            if property_id and unit_count > 0:
                try:
                    property_obj = Property.objects.get(id=property_id, landlord=request.user)
                    self.create_units_for_unit_type(property_obj, unit_type, unit_count)
                except Property.DoesNotExist:
                    return Response({"error": "Property not found or you do not have permission"}, status=404)
            
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    def create_units_for_unit_type(self, property_obj, unit_type, unit_count):
        """Create multiple units for a given unit type"""
        # Get existing units to determine next unit number
        existing_units = Unit.objects.filter(property_obj=property_obj)
        last_unit = existing_units.order_by('-unit_number').first()

        if last_unit and last_unit.unit_number.isdigit():
            start_number = int(last_unit.unit_number) + 1
        else:
            start_number = 1

        units_created = []
        for i in range(unit_count):
            unit_number = start_number + i
            unit_code = f"U-{property_obj.id}-{unit_type.name.replace(' ', '-')}-{unit_number}"

            unit = Unit.objects.create(
                property_obj=property_obj,
                unit_code=unit_code,
                unit_number=str(unit_number),
                unit_type=unit_type,
                is_available=True,
                rent=unit_type.rent,
                deposit=unit_type.deposit,
            )
            units_created.append(unit)

        # Invalidate caches after creating units
        cache.delete(f"landlord:{unit_type.landlord.id}:properties")
        cache.delete(f"property:{property_obj.id}:units")

        return units_created

class LandlordDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        landlord = request.user

        # Total active tenants: tenants assigned to units of this landlord and active
        total_active_tenants = CustomUser.objects.filter(
            user_type='tenant',
            is_active=True,
            unit__property_obj__landlord=landlord
        ).distinct().count()

        # Total units available
        total_units_available = Unit.objects.filter(
            property_obj__landlord=landlord,
            is_available=True
        ).count()

        # Total units occupied
        total_units_occupied = Unit.objects.filter(
            property_obj__landlord=landlord,
            is_available=False
        ).count()

        # Monthly revenue: sum of successful rent payments in the current month for this landlord
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Use created_at field instead of transaction_date
        monthly_revenue_agg = Payment.objects.filter(
            unit__property_obj__landlord=landlord,
            payment_type='rent',
            status='Success',
            created_at__gte=start_of_month,  # Changed from transaction_date
            created_at__lte=now  # Changed from transaction_date
        ).aggregate(total=Sum('amount'))
        monthly_revenue = monthly_revenue_agg['total'] or 0

        data = {
            "total_active_tenants": total_active_tenants,
            "total_units_available": total_units_available,
            "total_units_occupied": total_units_occupied,
            "monthly_revenue": float(monthly_revenue),
        }

        return Response(data)


class UnitTypeDetailView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get_object(self, pk, user):
        return UnitType.objects.get(id=pk, landlord=user)

    def get(self, request, pk):
        try:
            ut = self.get_object(pk, request.user)
            serializer = UnitTypeSerializer(ut)
            return Response(serializer.data)
        except UnitType.DoesNotExist:
            return Response({"error": "UnitType not found"}, status=404)

    def put(self, request, pk):
        try:
            ut = self.get_object(pk, request.user)
            serializer = UnitTypeSerializer(ut, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except UnitType.DoesNotExist:
            return Response({"error": "UnitType not found"}, status=404)

    def delete(self, request, pk):
        try:
            ut = self.get_object(pk, request.user)
            ut.delete()
            return Response({"message": "UnitType deleted"}, status=200)
        except UnitType.DoesNotExist:
            return Response({"error": "UnitType not found"}, status=404)


# Lists a single user (cached)
# View to get user details
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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


# New admin view to list landlords and their subscription statuses (superuser only)
class AdminLandlordSubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def get(self, request):
        landlords = CustomUser.objects.filter(user_type='landlord')
        data = []
        for landlord in landlords:
            subscription = getattr(landlord, 'subscription', None)
            status = 'Subscribed' if subscription and subscription.is_active() else 'Inactive or None'
            data.append({
                'landlord_id': landlord.id,
                'email': landlord.email,
                'name': landlord.full_name,
                'subscription_plan': subscription.plan if subscription else 'None',
                'subscription_status': status,
                'expiry_date': subscription.expiry_date if subscription else None,
            })
        return Response(data)


# Lists all tenants (cached)
# View to list all tenants (landlord only)
class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        cache_key = f"tenants:list:{request.user.id}"
        tenants_data = cache.get(cache_key)

        if not tenants_data:
            tenants = CustomUser.objects.filter(
                user_type="tenant",
                is_active=True,
                unit__property_obj__landlord=request.user
            ).distinct()
            serializer = UserSerializer(tenants, many=True)
            tenants_data = serializer.data
            cache.set(cache_key, tenants_data, timeout=300)

        return Response(tenants_data)


# Create a new user (invalidate cache)
# View to create a new user Landlord or Tenant
class UserCreateView(APIView):
    def post(self, request):
        print("Signup request received:", request.data)  # Debug logging
        
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            print(f"User created successfully: {user.email}, ID: {user.id}")  # Debug logging

            # Landlord onboarding: optionally auto-create properties and units if provided
            if user.user_type == 'landlord':
                # Expect optional 'properties' array in request.data, each item: {name, city, state, unit_count, vacant_units}
                properties = request.data.get('properties')
                from .models import Property, Unit, UnitType
                import uuid

                if properties and isinstance(properties, list):
                    for prop in properties:
                        name = prop.get('name') or f"Property-{uuid.uuid4().hex[:6].upper()}"
                        city = prop.get('city', '')
                        state = prop.get('state', '')
                        unit_count = int(prop.get('unit_count', 0))
                        p = Property.objects.create(landlord=user, name=name, city=city, state=state, unit_count=unit_count)

                        # Create at least one unit if unit_count > 0
                        for i in range(1, unit_count + 1):
                            unit_number = str(i)
                            unit_code = f"U-{p.id}-{i}"
                            # Determine vacancy status based on optional vacant_units or default all vacant
                            vacant_units = int(prop.get('vacant_units', unit_count))
                            is_available = i <= vacant_units

                            # Optionally link to a unit_type if provided via name
                            unit_type_obj = None
                            unit_type_name = prop.get('unit_type')
                            if unit_type_name:
                                unit_type_obj, _ = UnitType.objects.get_or_create(landlord=user, name=unit_type_name)

                            Unit.objects.create(
                                property_obj=p,
                                unit_code=unit_code,
                                unit_number=unit_number,
                                unit_type=unit_type_obj,
                                is_available=is_available,
                                rent=unit_type_obj.rent if unit_type_obj else 0,
                                deposit=unit_type_obj.deposit if unit_type_obj else 0,
                            )

            # Tenant created: attempt to assign unit if landlord_code and unit_code provided
            if user.user_type == "tenant":
                cache.delete("tenants:list")
                landlord_code = request.data.get('landlord_code')
                unit_code = request.data.get('unit_code')
                if landlord_code and unit_code:
                    try:
                        landlord = CustomUser.objects.get(landlord_code=landlord_code, user_type='landlord')
                        unit = Unit.objects.get(unit_code=unit_code, property_obj__landlord=landlord)
                        # Check for deposit payments
                        from payments.models import Payment
                        deposit_payments = Payment.objects.filter(
                            tenant=user,
                            unit=unit,
                            payment_type='deposit',
                            status='Success',
                            amount__gte=unit.deposit
                        )
                        if deposit_payments.exists():
                            unit.tenant = user
                            unit.is_available = False
                            unit.save()
                        else:
                            # leave unassigned; frontend should request deposit
                            pass
                    except CustomUser.DoesNotExist:
                        # landlord not found; ignore
                        pass
                    except Unit.DoesNotExist:
                        pass

            return Response(serializer.data, status=201)
        else:
            print("Serializer errors:", serializer.errors)  # Debug logging
            return Response(serializer.errors, status=400)


# Create a new property (invalidate landlord cache)
# View to create a new property (landlord only)
PLAN_LIMITS = {
    "free": 2,         # trial landlords can only create 2 properties
    "starter": 3,      # starter (up to 10 units) -> small number of properties
    "basic": 10,       # basic (10-50 units)
    "professional": 25,# professional (50-100 units)
    "onetime": None,   # unlimited
}

class CreatePropertyView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def post(self, request):
        logger.info(f"CreatePropertyView: User {request.user.id} attempting to create property")
        user = request.user

        # Fetch subscription
        try:
            subscription = Subscription.objects.get(user=user)
            logger.info(f"Subscription found: {subscription.plan}")
        except Subscription.DoesNotExist:
            logger.error(f"No subscription found for user {user.id}")
            return Response({"error": "No active subscription found."}, status=403)

        plan = subscription.plan.lower()

        # Check if subscription is active
        if not subscription.is_active():
            logger.warning(f"Subscription expired for user {user.id}")
            return Response({"error": "Your subscription has expired. Please renew or upgrade."}, status=403)

        # Get plan limit
        max_properties = PLAN_LIMITS.get(plan)
        if max_properties is None and plan != "onetime":
            return Response({"error": f"Unknown plan type: {plan}"}, status=400)

        # Count current properties
        current_count = Property.objects.filter(landlord=user).count()
        logger.info(f"Current properties count: {current_count}, max: {max_properties}")
        if plan != "onetime" and current_count >= max_properties:
            return Response({
                "error": f"Your current plan ({plan}) allows a maximum of {max_properties} properties. Upgrade to add more."
            }, status=403)

        # Proceed with creation
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            logger.info(f"Serializer valid, saving property for user {user.id}")
            property = serializer.save(landlord=user)
            try:
                cache.delete(f"landlord:{user.id}:properties")  # clear cache if you're caching landlord properties
                logger.info(f"Cache cleared for user {user.id}")
            except Exception as e:
                logger.warning(f"Cache delete failed: {e}")
            logger.info(f"Property created successfully: {property.id}")
            return Response(serializer.data, status=201)

        logger.error(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=400)

# List landlord properties (cached)
class LandlordPropertiesView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

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
class CreateUnitView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def post(self, request):
        serializer = UnitSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            unit = serializer.save()
            cache.delete(f"landlord:{request.user.id}:properties")
            cache.delete(f"property:{unit.property_obj.id}:units")
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# List units of a property (cached)
class PropertyUnitsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request, property_id):
        cache_key = f"property:{property_id}:units"
        units_data = cache.get(cache_key)

        if not units_data:
            try:
                property = Property.objects.get(id=property_id, landlord=request.user)
                units = Unit.objects.filter(property_obj=property)
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
class AssignTenantView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, unit_id, tenant_id):
        logger.info(f"AssignTenantView: Landlord {request.user.id} attempting to assign tenant {tenant_id} to unit {unit_id}")

        try:
            # Validate unit exists and belongs to landlord
            unit = Unit.objects.get(id=unit_id, property_obj__landlord=request.user)
            logger.info(f"Unit found: {unit.unit_code}, available: {unit.is_available}")

            # Validate unit is available
            if not unit.is_available:
                logger.warning(f"Unit {unit_id} is not available for assignment")
                return Response({
                    "error": "Unit is not available for assignment",
                    "status": "failed"
                }, status=400)

            # Validate tenant exists and is a tenant
            tenant = CustomUser.objects.get(id=tenant_id, user_type="tenant")
            logger.info(f"Tenant found: {tenant.full_name} (ID: {tenant.id})")

            # Check if tenant already has a unit assigned
            existing_unit = Unit.objects.filter(tenant=tenant).first()
            if existing_unit:
                logger.warning(f"Tenant {tenant_id} already has unit {existing_unit.id} assigned")
                return Response({
                    "error": f"Tenant already has unit {existing_unit.unit_number} assigned",
                    "status": "failed"
                }, status=400)

            # CHECK IF DEPOSIT IS PAID BEFORE ASSIGNMENT
            from payments.models import Payment
            deposit_paid = Payment.objects.filter(
                tenant=tenant,
                unit=unit,
                payment_type='deposit',
                status='Success',
                amount__gte=unit.deposit
            ).exists()
            
            if not deposit_paid:
                logger.warning(f"Tenant {tenant_id} has not paid deposit for unit {unit_id}")
                return Response({
                    "error": "Tenant must pay deposit before being assigned to unit",
                    "status": "failed"
                }, status=400)

            # If deposit is paid, assign tenant immediately
            unit.tenant = tenant
            unit.is_available = False
            unit.save()

            # Invalidate caches
            cache.delete(f"landlord:{request.user.id}:properties")
            cache.delete(f"property:{unit.property_obj.id}:units")

            logger.info(f"✅ Tenant {tenant.full_name} assigned to unit {unit.unit_number}")

            return Response({
                'message': f'Tenant {tenant.full_name} successfully assigned to unit {unit.unit_number}',
                'status': 'success'
            }, status=200)

        except Unit.DoesNotExist:
            logger.error(f"Unit {unit_id} not found or not owned by landlord {request.user.id}")
            return Response({
                "error": "Unit not found or you do not have permission",
                "status": "failed"
            }, status=404)
        except CustomUser.DoesNotExist:
            logger.error(f"Tenant {tenant_id} not found or invalid user type")
            return Response({
                "error": "Tenant not found or invalid user type",
                "status": "failed"
            }, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in AssignTenantView: {str(e)}")
            return Response({
                "error": "An unexpected error occurred",
                "status": "failed"
            }, status=500)


# Password reset
class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password reset email sent."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Update property
class UpdatePropertyView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def put(self, request, property_id):
        try:
            property = Property.objects.get(id=property_id, landlord=request.user)
            serializer = PropertySerializer(property, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"landlord:{request.user.id}:properties")
                cache.delete(f"property:{property_id}:units")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Property.DoesNotExist:
            return Response({"error": "Property not found or you do not have permission"}, status=404)

    def delete(self, request, property_id):
        try:
            property = Property.objects.get(id=property_id, landlord=request.user)
            property.delete()
            cache.delete(f"landlord:{request.user.id}:properties")
            cache.delete(f"property:{property_id}:units")
            return Response({"message": "Property deleted successfully."}, status=200)
        except Property.DoesNotExist:
            return Response({"error": "Property not found or you do not have permission"}, status=404)

# Update unit
class UpdateUnitView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def put(self, request, unit_id):
        try:
            unit = Unit.objects.get(id=unit_id, property_obj__landlord=request.user)
            serializer = UnitSerializer(unit, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"landlord:{request.user.id}:properties")
                cache.delete(f"property:{unit.property_obj.id}:units")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found or you do not have permission"}, status=404)

    def delete(self, request, unit_id):
        try:
            unit = Unit.objects.get(id=unit_id, property_obj__landlord=request.user)
            property_id = unit.property_obj.id
            unit.delete()
            cache.delete(f"landlord:{request.user.id}:properties")
            cache.delete(f"property:{property_id}:units")
            return Response({"message": "Unit deleted successfully."}, status=200)
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found or you do not have permission"}, status=404)


class TenantUpdateUnitView(APIView):
    permission_classes = [IsAuthenticated, IsTenant]

    def put(self, request):
        try:
            unit = Unit.objects.get(tenant=request.user)
            serializer = UnitNumberSerializer(unit, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                cache.delete(f"property:{unit.property_obj.id}:units")
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Unit.DoesNotExist:
            return Response({"error": "No unit assigned to you"}, status=404)

# Update user
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


class AdjustRentView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def post(self, request):
        landlord = request.user
        adjustment_type = request.data.get('adjustment_type')  # 'percentage' or 'fixed'
        value = request.data.get('value')  # decimal, positive for increase, negative for decrease
        unit_type_id = request.data.get('unit_type_id')  # optional, if provided, adjust only units of this type

        logger.info(f"AdjustRentView POST: Landlord {landlord.id} adjusting rent, adjustment_type={adjustment_type}, value={value}, unit_type_id={unit_type_id}")

        if adjustment_type not in ['percentage', 'fixed']:
            return Response({"error": "adjustment_type must be 'percentage' or 'fixed'"}, status=400)

        try:
            value = Decimal(value)
        except (ValueError, TypeError):
            return Response({"error": "value must be a valid number"}, status=400)

        # Filter units
        units = Unit.objects.filter(property_obj__landlord=landlord)
        if unit_type_id:
            try:
                unit_type = UnitType.objects.get(id=unit_type_id, landlord=landlord)
                units = units.filter(unit_type=unit_type)
            except UnitType.DoesNotExist:
                return Response({"error": "UnitType not found or not owned by you"}, status=404)

        updated_count = 0
        for unit in units:
            old_rent = unit.rent
            if adjustment_type == 'percentage':
                new_rent = old_rent * (Decimal(1) + value / Decimal(100))
            else:  # fixed
                new_rent = old_rent + value
            # Ensure rent doesn't go negative
            new_rent = max(Decimal(0), new_rent)
            unit.rent = new_rent
            unit.save()  # This will update rent_remaining
            updated_count += 1

        logger.info(f"AdjustRentView POST: Rent adjusted for {updated_count} units by landlord {landlord.id}")

        # Invalidate caches
        cache.delete(f"landlord:{landlord.id}:properties")
        # Also invalidate rent_summary cache
        from payments.views import RentSummaryView
        cache.delete(f"rent_summary:{landlord.id}")

        return Response({"message": f"Rent adjusted for {updated_count} units successfully"})

    def put(self, request):
        landlord = request.user
        new_rent = request.data.get('new_rent')
        unit_type_id = request.data.get('unit_type_id')  # optional

        logger.info(f"AdjustRentView PUT: Landlord {landlord.id} setting new rent, new_rent={new_rent}, unit_type_id={unit_type_id}")

        if new_rent is None:
            return Response({"error": "new_rent is required"}, status=400)

        try:
            new_rent = Decimal(new_rent)
        except (ValueError, TypeError):
            return Response({"error": "new_rent must be a valid number"}, status=400)

        units = Unit.objects.filter(property_obj__landlord=landlord)
        if unit_type_id:
            try:
                unit_type = UnitType.objects.get(id=unit_type_id, landlord=landlord)
                units = units.filter(unit_type=unit_type)
            except UnitType.DoesNotExist:
                return Response({"error": "UnitType not found or not owned by you"}, status=404)

        updated_count = 0
        for unit in units:
            unit.rent = new_rent
            unit.save()
            updated_count += 1

        logger.info(f"AdjustRentView PUT: Rent set to {new_rent} for {updated_count} units by landlord {landlord.id}")

        # Invalidate caches
        cache.delete(f"landlord:{landlord.id}:properties")
        from payments.views import RentSummaryView
        cache.delete(f"rent_summary:{landlord.id}")

        return Response({"message": f"Rent set to {new_rent} for {updated_count} units successfully"})

# View to check subscription status (landlord only)
class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord]

    def get(self, request):
        user = request.user
        try:
            subscription = Subscription.objects.get(user=user)
            data = {
                "plan": subscription.plan,
                "is_active": subscription.is_active(),
                "expiry_date": subscription.expiry_date,
                "status": "Subscribed" if subscription.is_active() else "Inactive"
            }
        except Subscription.DoesNotExist:
            data = {"status": "No subscription found"}
        return Response(data)

# View to update landlord's Mpesa till number (landlord only)
class UpdateTillNumberView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def patch(self, request):
        user = request.user
        till_number = request.data.get('mpesa_till_number')
        if not till_number:
            return Response({"error": "mpesa_till_number is required"}, status=400)

        user.mpesa_till_number = till_number
        user.save()
        return Response({"message": "Till number updated successfully", "mpesa_till_number": till_number})

    def put(self, request):
        return self.patch(request)


# Endpoint to get or update the currently authenticated user
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # invalidate cache for this user
            cache.delete(f"user:{request.user.id}")
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def put(self, request):
        return self.patch(request)


# View to update tenant reminder preferences
class UpdateReminderPreferencesView(APIView):
    permission_classes = [IsAuthenticated, IsTenant]

    def patch(self, request):
        serializer = ReminderPreferencesSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# Password reset confirm view
class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View to list available units for landlords to share with tenants
class LandlordAvailableUnitsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        units = Unit.objects.filter(property_obj__landlord=request.user, is_available=True)
        serializer = AvailableUnitsSerializer(units, many=True)
        return Response(serializer.data)


# New endpoint to log requests and return a welcome message
class WelcomeView(APIView):
    def get(self, request):
        logger.info(f"Request received: {request.method} {request.path}")
        return Response({"message": "Welcome to the Makau Rentals API!"})


class LandlordsListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def get(self, request):
        landlords = CustomUser.objects.filter(user_type='landlord')
        data = []
        for landlord in landlords:
            subscription = getattr(landlord, 'subscription', None)
            status = 'Subscribed' if subscription and subscription.is_active() else 'Inactive or None'
            data.append({
                'id': landlord.id,
                'email': landlord.email,
                'name': landlord.full_name,
                'subscription_plan': subscription.plan if subscription else 'None',
                'subscription_status': status,
                'expiry_date': subscription.expiry_date if subscription else None,
            })
        return Response(data)


class PendingApplicationsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        # For now, return tenants without assigned units (pending applications)
        tenants = CustomUser.objects.filter(
            user_type="tenant",
            is_active=True,
            unit__isnull=True
        )
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)


class EvictedTenantsView(APIView):
    permission_classes = [IsAuthenticated, IsLandlord, HasActiveSubscription]

    def get(self, request):
        # For now, return inactive tenants that were previously assigned to landlord's units
        evicted_tenants = CustomUser.objects.filter(
            user_type="tenant",
            is_active=False,
            unit__property_obj__landlord=request.user
        ).distinct()
        serializer = UserSerializer(evicted_tenants, many=True)
        return Response(serializer.data)
# Add this view to your views.py to validate and fetch landlord data

class ValidateLandlordView(APIView):
    """Endpoint to validate landlord ID and fetch their properties"""
    
    def post(self, request):
        landlord_code = request.data.get('landlord_code')
        
        print(f"🔍 Validating landlord with code: {landlord_code}")  # DEBUG
        
        if not landlord_code:
            return Response({
                'error': 'Landlord code is required'
            }, status=400)
        
        try:
            # Find landlord by landlord_code
            landlord = CustomUser.objects.get(
                landlord_code=landlord_code,
                user_type='landlord',
                is_active=True
            )
            
            print(f"✅ Landlord found: {landlord.full_name} (ID: {landlord.id})")  # DEBUG
            
            # Get properties for this landlord
            properties = Property.objects.filter(landlord=landlord)
            print(f"📊 Found {properties.count()} properties for landlord")  # DEBUG
            
            properties_data = []
            for property_obj in properties:
                print(f"🏠 Processing property: {property_obj.name} (ID: {property_obj.id})")  # DEBUG
                
                # Get available units for this property
                try:
                    # Try different related names
                    available_units = None
                    
                    if hasattr(property_obj, 'units'):
                        available_units = property_obj.units.filter(
                            is_available=True,
                            tenant__isnull=True
                        )
                        print(f"   Using 'units' related name, found {available_units.count()} available units")  # DEBUG
                    elif hasattr(property_obj, 'unit_set'):
                        available_units = property_obj.unit_set.filter(
                            is_available=True,
                            tenant__isnull=True
                        )
                        print(f"   Using 'unit_set' related name, found {available_units.count()} available units")  # DEBUG
                    else:
                        # Fallback: direct query
                        available_units = Unit.objects.filter(
                            property_obj=property_obj,
                            is_available=True,
                            tenant__isnull=True
                        )
                        print(f"   Using direct query, found {available_units.count()} available units")  # DEBUG
                        
                except Exception as e:
                    print(f"   ❌ Error accessing units: {e}")  # DEBUG
                    continue
                
                if available_units and available_units.exists():
                    units_data = []
                    for unit in available_units:
                        unit_data = {
                            'id': unit.id,
                            'unit_number': unit.unit_number,
                            'unit_code': unit.unit_code,
                            'rent': float(unit.rent),
                            'deposit': float(unit.deposit),
                        }
                        
                        # Add room type info if available
                        if hasattr(unit, 'unit_type') and unit.unit_type:
                            unit_data['room_type'] = unit.unit_type.name
                        else:
                            unit_data['room_type'] = 'N/A'
                            
                        # Add bedroom/bathroom info
                        if hasattr(unit, 'bedrooms'):
                            unit_data['bedrooms'] = unit.bedrooms
                        else:
                            unit_data['bedrooms'] = 0
                            
                        if hasattr(unit, 'bathrooms'):
                            unit_data['bathrooms'] = unit.bathrooms
                        else:
                            unit_data['bathrooms'] = 1
                        
                        units_data.append(unit_data)
                        print(f"   ✅ Added unit: {unit.unit_number}")  # DEBUG
                    
                    properties_data.append({
                        'id': property_obj.id,
                        'name': property_obj.name,
                        'address': f"{getattr(property_obj, 'city', '')}, {getattr(property_obj, 'state', '')}",
                        'units': units_data
                    })
                    print(f"   🏢 Added property with {len(units_data)} units")  # DEBUG
                else:
                    print(f"   ⚠️  No available units for property {property_obj.name}")  # DEBUG
            
            print(f"📦 Final properties data: {len(properties_data)} properties with available units")  # DEBUG
            
            if not properties_data:
                return Response({
                    'error': 'This landlord has no available units at the moment'
                }, status=404)
            
            return Response({
                'landlord_id': landlord.id,
                'landlord_name': landlord.full_name,
                'landlord_email': landlord.email,
                'landlord_phone': getattr(landlord, 'phone_number', ''),
                'properties': properties_data
            }, status=200)
            
        except CustomUser.DoesNotExist:
            print(f"❌ Landlord not found with code: {landlord_code}")  # DEBUG
            return Response({
                'error': 'Landlord ID not found. Please check and try again.'
            }, status=404)
        except Exception as e:
            print(f"💥 Unexpected error: {str(e)}")  # DEBUG
            logger.error(f"Error in ValidateLandlordView: {str(e)}")
            return Response({
                'error': 'Internal server error while validating landlord'
            }, status=500)


# Update your TenantRegistrationStepView to handle Step 2 validation
class TenantRegistrationStepView(APIView):
    def post(self, request, step):
        try:
            data = request.data.copy()  # Make a copy to avoid mutating original
            session_id = data.get('session_id') or str(uuid.uuid4())
            
            # STEP 2: Validate landlord ID before saving
            if step == 2:
                landlord_id = data.get('landlord_id')
                if landlord_id:
                    try:
                        # Verify landlord exists and is active
                        landlord = CustomUser.objects.get(
                            landlord_code=landlord_id,
                            user_type='landlord',
                            is_active=True
                        )
                        
                        # Add landlord info to cached data
                        data['landlord_db_id'] = landlord.id
                        data['verified'] = True
                        
                    except CustomUser.DoesNotExist:
                        return Response({
                            'error': 'Landlord ID not found. Please check and try again.',
                            'status': 'failed'
                        }, status=400)
            
            # Store step data in cache
            cache_key = f"tenant_registration_{session_id}_step_{step}"
            cache.set(cache_key, data, timeout=3600)  # 1 hour expiry
            
            return Response({
                'session_id': session_id,  # Make sure this is returned
                'step': step,
                'status': 'saved',
                'message': f'Step {step} data saved successfully'
            })
            
        except Exception as e:
            logger.error(f"Error in TenantRegistrationStepView: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'status': 'failed'
            }, status=500)
        
class LandlordRegistrationStepView(APIView):
    def post(self, request, step):
        data = request.data
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        # Store step data in cache
        cache_key = f"landlord_registration_{session_id}_step_{step}"
        cache.set(cache_key, data, timeout=3600)
        
        return Response({
            'session_id': session_id,
            'step': step,
            'status': 'saved',
            'message': f'Step {step} data saved successfully'
        })

class CompleteTenantRegistrationView(APIView):
    def post(self, request):
        data = request.data
        session_id = data.get('session_id')
        
        # Retrieve all step data from cache
        all_data = {}
        for step in range(2, 7):  # Steps 2-6
            cache_key = f"tenant_registration_{session_id}_step_{step}"
            step_data = cache.get(cache_key)
            if step_data:
                all_data.update(step_data)
        
        # Merge with final data
        all_data.update(data)
        
        # Create the user (your existing user creation logic)
        try:
            user = CustomUser.objects.create_user(
                email=all_data['email'],
                full_name=all_data['full_name'],
                user_type='tenant',
                password=all_data['password'],
                phone_number=all_data['phone_number'],
                government_id=all_data['government_id'],
                emergency_contact=all_data['emergency_contact']
            )
            
            # Clean up cache
            for step in range(2, 7):
                cache_key = f"tenant_registration_{session_id}_step_{step}"
                cache.delete(cache_key)
            
            return Response({
                'status': 'success',
                'user_id': user.id,
                'message': 'Tenant registration completed successfully'
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)
class CompleteLandlordRegistrationView(APIView):
    def post(self, request):
        """
        Complete landlord registration after all steps are done
        """
        try:
            data = request.data
            session_id = data.get('session_id')
            
            if not session_id:
                return Response({
                    'status': 'error',
                    'message': 'Session ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve all step data from cache
            all_data = {}
            for step in range(2, 5):
                cache_key = f"landlord_registration_{session_id}_step_{step}"
                step_data = cache.get(cache_key)
                if step_data:
                    step_data.pop('step', None)
                    all_data.update(step_data)

            all_data.update(data)
            
            # Validate required fields
            required_fields = ['full_name', 'email', 'phone_number', 'national_id', 
                             'mpesa_till_number', 'password']
            
            missing_fields = [field for field in required_fields if not all_data.get(field)]
            if missing_fields:
                return Response({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if email already exists
            if CustomUser.objects.filter(email=all_data['email']).exists():
                return Response({
                    'status': 'error',
                    'message': 'Email already exists'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create the landlord user
            try:
                user_data = {
                    'email': all_data['email'],
                    'full_name': all_data['full_name'],
                    'user_type': 'landlord',
                    'password': all_data['password'],
                    'phone_number': all_data['phone_number'],
                    'government_id': all_data['national_id'],
                    'mpesa_till_number': all_data['mpesa_till_number'],
                }
                
                # Add optional fields if they exist
                if 'address' in all_data:
                    user_data['address'] = all_data['address']
                if 'website' in all_data:
                    user_data['website'] = all_data['website']

                landlord = CustomUser.objects.create_user(**user_data)

                # Create properties and units if provided
                properties_data = all_data.get('properties', [])
                created_properties = []
                
                for property_data in properties_data:
                    try:
                        # Create property
                        property_obj = Property.objects.create(
                            landlord=landlord,
                            name=property_data.get('name', f'Property-{uuid.uuid4().hex[:6].upper()}'),
                            city='Nairobi',
                            state='Nairobi',
                            unit_count=len(property_data.get('units', []))
                        )
                        
                        # Create units for this property
                        units_data = property_data.get('units', [])
                        created_units = []
                        
                        for i, unit_data in enumerate(units_data, 1):
                            # Create unit type if it doesn't exist
                            room_type = unit_data.get('room_type', 'studio')
                            unit_type, created = UnitType.objects.get_or_create(
                                landlord=landlord,
                                name=room_type,
                                defaults={
                                    'deposit': Decimal('0.00'),
                                    'rent': Decimal(unit_data.get('monthlyRent', '0')),
                                    'number_of_units': 0
                                }
                            )
                            
                            # Generate unique unit code
                            unit_number = unit_data.get('unitNumber', f'Unit-{i}')
                            unit_code = f"U-{property_obj.id}-{unit_number}-{uuid.uuid4().hex[:8]}"
                            
                            # Create the unit
                            unit = Unit.objects.create(
                                property_obj=property_obj,
                                unit_code=unit_code,  # Use the unique generated code
                                unit_number=unit_number,
                                bedrooms=self.get_bedroom_count(room_type),
                                bathrooms=1,
                                unit_type=unit_type,
                                rent=Decimal(unit_data.get('monthlyRent', '0')),
                                deposit=Decimal(unit_data.get('monthlyRent', '0')),  # Deposit = 1 month rent
                                is_available=True
                            )
                            created_units.append(unit.id)
                        
                        created_properties.append({
                            'id': property_obj.id,
                            'name': property_obj.name,
                            'units_count': len(created_units)
                        })
                        
                    except Exception as prop_error:
                        logger.error(f"Error creating property: {str(prop_error)}")
                        continue

                # FIX 2: Check if subscription already exists before creating
                try:
                    subscription = Subscription.objects.get(user=landlord)
                    # Subscription already exists (was created by CustomUserManager)
                    logger.info(f"Subscription already exists for user {landlord.id}")
                except Subscription.DoesNotExist:
                    # Create subscription for landlord (free trial)
                    subscription = Subscription.objects.create(
                        user=landlord,
                        plan="free",
                        expiry_date=timezone.now() + timedelta(days=60)
                    )
                    logger.info(f"Created new subscription for user {landlord.id}")

                # Clean up cache
                for step in range(2, 5):
                    cache_key = f"landlord_registration_{session_id}_step_{step}"
                    cache.delete(cache_key)

                # Prepare response data
                response_data = {
                    'status': 'success',
                    'user_id': landlord.id,
                    'landlord_code': landlord.landlord_code,
                    'email': landlord.email,
                    'full_name': landlord.full_name,
                    'properties_created': created_properties,
                    'subscription': {
                        'plan': subscription.plan,
                        'expiry_date': subscription.expiry_date
                    },
                    'message': 'Landlord registration completed successfully'
                }

                # Send welcome email
                self.send_welcome_email(landlord)

                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Error creating landlord user: {str(e)}")
                # If user creation fails but user was created, delete it
                if 'landlord' in locals():
                    landlord.delete()
                return Response({
                    'status': 'error',
                    'message': 'Failed to create landlord account'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in landlord registration: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_bedroom_count(self, room_type):
        """
        Map room type string to bedroom count
        """
        room_type_mapping = {
            'studio': 0,
            '1-bedroom': 1,
            '2-bedroom': 2,
            '3-bedroom': 3
        }
        return room_type_mapping.get(room_type, 0)

    def send_welcome_email(self, landlord):
        """
        Send welcome email to landlord
        """
        try:
            subject = "Welcome to Makao Rentals - Your Landlord Account is Ready!"
            message = f"""
            Hello {landlord.full_name},

            Welcome to  Makao Rentals! Your landlord account has been successfully created.

            Account Details:
            - Landlord Code: {landlord.landlord_code}
            - Email: {landlord.email}
            - M-Pesa Till: {landlord.mpesa_till_number}

            Your 60-day free trial has been activated. You can now:
            - Manage your properties
            - Add units and set rents
            - Receive rent payments via M-Pesa
            - Track tenant payments

            Login to your dashboard to get started.

            Best regards,
            Makao Rentals Team
            """

            logger.info(f"Welcome email prepared for {landlord.email}: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")