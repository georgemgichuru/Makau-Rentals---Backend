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
import logging

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
        monthly_revenue_agg = Payment.objects.filter(
            unit__property_obj__landlord=landlord,
            payment_type='rent',
            status='Success',
            transaction_date__gte=start_of_month,
            transaction_date__lte=now
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
