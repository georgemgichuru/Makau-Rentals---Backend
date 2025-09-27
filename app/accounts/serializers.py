from accounts.models import CustomUser,Property, Unit   
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'user_type', 'is_active', 'is_staff', 'is_superuser']
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff', 'is_superuser']
        if model.user_type == 'landlord':
            fields.append('properties')  # Assuming a related name 'properties' for landlord's properties
            is_staff = True  # Landlords are staff members
        if model.user_type == 'tenant':
            fields.append('rentals')  # Assuming a related name 'rentals' for tenant's rentals
            is_staff = False  # Tenants are not staff members
        extra_kwargs = {
            'password': {'write_only': True}
        }
        def create(self, validated_data):
            user = CustomUser.objects.create_user(**validated_data)
            return user
        
        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                if attr == 'password':
                    instance.set_password(value)
                else:
                    setattr(instance, attr, value)
            instance.save()
            return instance
        
class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'landlord', 'name', 'city', 'state', 'units']
        read_only_fields = ['id', 'landlord']
    def create(self, validated_data):
        property = Property.objects.create(**validated_data)
        return property
    
class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'property', 'unit_number', 'floor', 'bedrooms', 'bathrooms', 'rent', 'tenant', 'rent_paid', 'rent_remaining', 'deposit', 'is_available']
        read_only_fields = ['id', 'rent_paid', 'rent_remaining']
    def create(self, validated_data):
        unit = Unit.objects.create(**validated_data)
        return unit

# TODO: Ensure landlords create properties and units upon sign up this will be done in the frontend
# TODO: Ensure Tenants pay the deposit to book a unit and choose their property upon sign up
# TODO: Ensure Landlords approve their tenants before they can pay rent upon tenant sign up
# TODO: Ensure Tenants and Landlords can reset their passwords and get email notifications for important actions 
