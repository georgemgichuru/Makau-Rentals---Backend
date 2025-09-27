from serializers import UserSerializer,PasswordResetSerializer
from models import CustomUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from serializers import PropertySerializer, UnitSerializer
from rest_framework.permissions import IsAuthenticated, login_required
from models import Property, Unit
from .permissions import IsLandlord, IsTenant


#Lists all users both tenants and landlords
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, login_required]
    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

# To list the list of all users
# TODO: List only for admin users and list only tenants for landlords
class UserListView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsLandlord]
    def get(self, request):
        tenants = CustomUser.objects.filter(user_type='tenant')
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)
    
# To create a new user basically for registration
class UserCreateView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# View to create a new property
class CreatePropertyView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsLandlord]
    def post(self, request):
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(landlord=request.user)  # Assuming the user is authenticated
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
# View to list all properties of a landlord
class LandlordPropertiesView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsLandlord]
    def get(self, request):
        properties = Property.objects.filter(landlord=request.user)
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)
#Class to create a new unit under a property
class CreateUnitView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsLandlord]
    def post(self, request):
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Assuming the user is authenticated
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# Class to list all units of a property
class PropertyUnitsView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsLandlord]
    def get(self, request, property_id):
        try:
            property = Property.objects.get(id=property_id, landlord=request.user)
            units = Unit.objects.filter(property=property)
            serializer = UnitSerializer(units, many=True)
            return Response(serializer.data)
        except Property.DoesNotExist:
            return Response({"error": "Property not found or you do not have permission"}, status=404)
# Class to associate tenants to landlords via units so we enter them to the unit model
class AssignTenantToUnitView(APIView):
    permission_classes = [IsAuthenticated, login_required, IsTenant]
    def post(self, request, unit_id, tenant_id):
        try:
            unit = Unit.objects.get(id=unit_id)
            tenant = CustomUser.objects.get(id=tenant_id, user_type='tenant')
            unit.tenant = tenant
            unit.is_available = False  # Mark the unit as not available
            unit.save()
            return Response({"message": "Tenant assigned to unit successfully"})
        except Unit.DoesNotExist:
            return Response({"error": "Unit not found"}, status=404)
        except CustomUser.DoesNotExist:
            return Response({"error": "Tenant not found or invalid user type"}, status=404)

# View to handle password reset requests
class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


