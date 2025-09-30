from accounts.models import CustomUser,Property, Unit   
from rest_framework import serializers

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

# Overide the token to use email instead of username for JWT authentication
# accounts/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"



from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'user_type',
            'is_active',
            'is_staff',
            'is_superuser',
            'password'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff', 'is_superuser']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        # Always use the manager to ensure password is hashed
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
# TODO: Ensure Tenants and Landlords can reset their passwords and get email notifications for important actions 


# For reset password functionality
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # Assuming you have a frontend URL to handle password resets
        # TODO: Update the frontend URL
        reset_link = f"http://yourfrontend.com/reset-password/{uid}/{token}/" 

        send_mail(
            subject="Password Reset Request",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=None,
            recipient_list=[email],
        )
