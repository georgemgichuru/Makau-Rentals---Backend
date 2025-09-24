from accounts.models import CustomUser
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
        
# TODO: Add Property and Unit serializers as needed
# TODO: Ensure landlords create properties and units upon sign up
# TODO: Ensure Tenants pay the deposit to book a unit and choose their property upon sign up
# TODO: Ensure Landlords approve their tenants before they can pay rent upon tenant sign up
# TODO: Ensure Tenants and Landlords can reset their passwords and get email notifications for important actions 
