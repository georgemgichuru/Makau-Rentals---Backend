from .models import CustomUser, Property, Unit, UnitType
from rest_framework import serializers

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

# Overide the token to use email instead of username for JWT authentication
# accounts/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    user_type = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user_type = attrs.get("user_type")

        if email and password and user_type:
            user = authenticate(self.context['request'], email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password")
            if user.user_type not in ['tenant', 'landlord']:
                raise serializers.ValidationError("Invalid user type")
            if user.user_type != user_type:
                raise serializers.ValidationError("User type does not match")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
        else:
            raise serializers.ValidationError("Must include 'email', 'password', and 'user_type'")

        data = super().validate(attrs)
        data['user_type'] = user_type
        return data



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'full_name',
            'government_id',
            'id_document',
            'landlord_code',
            'date_joined',
            'user_type',
            'is_active',
            'is_staff',
            'is_superuser',
            'mpesa_till_number',
            'phone_number',
            'emergency_contact',
            'reminder_mode',
            'reminder_value',
            'password'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff', 'is_superuser', 'landlord_code']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        # Always use the manager to ensure password is hashed
        # adapt to new signature: email, full_name, user_type, password
        email = validated_data.pop('email')
        full_name = validated_data.pop('full_name')
        user_type = validated_data.pop('user_type')
        password = validated_data.pop('password', None)
        user = CustomUser.objects.create_user(email=email, full_name=full_name, user_type=user_type, password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

    def validate_phone_number(self, value):
        if not value:
            return value
        import re
        if not re.match(r"^\+?[0-9]{7,15}$", value):
            raise serializers.ValidationError("Enter a valid phone number in international format, e.g. +2547XXXXXXXX")
        return value

    def validate_emergency_contact(self, value):
        if not value:
            return value
        import re
        if not re.match(r"^\+?[0-9]{7,15}$", value):
            raise serializers.ValidationError("Enter a valid emergency contact phone number in international format")
        return value

        
class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'landlord', 'name', 'city', 'state', 'unit_count']
        read_only_fields = ['id', 'landlord']
    def create(self, validated_data):
        property = Property.objects.create(**validated_data)
        return property
    
class UnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitType
        fields = ['id', 'landlord', 'name', 'deposit', 'rent']
        read_only_fields = ['id', 'landlord']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'property_obj', 'unit_code', 'unit_number', 'floor', 'bedrooms', 'bathrooms', 'unit_type', 'rent', 'tenant', 'rent_paid', 'rent_remaining', 'deposit', 'is_available']
        read_only_fields = ['id', 'rent_remaining', 'unit_code']

    def create(self, validated_data):
        # Auto-generate unit_code if not provided
        if not validated_data.get('unit_code'):
            prop = validated_data.get('property_obj') or validated_data.get('property')
            # Determine next index for unit under property
            if prop and getattr(prop, 'id', None):
                existing_count = Unit.objects.filter(property_obj=prop).count()
                validated_data['unit_code'] = f"U-{prop.id}-{existing_count+1}"
            else:
                # fallback unique code
                import uuid
                validated_data['unit_code'] = f"U-{uuid.uuid4().hex[:10].upper()}"
        # Enforce landlord has at least one UnitType defined before creating units
        prop = validated_data.get('property_obj') or validated_data.get('property')
        if prop and prop.landlord:
            landlord = prop.landlord
            if not UnitType.objects.filter(landlord=landlord).exists():
                raise serializers.ValidationError("Landlord must create at least one UnitType before creating Units.")

        unit = Unit.objects.create(**validated_data)
        return unit


class UnitNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['unit_number']

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
        from django.conf import settings
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # Use the configurable frontend URL from settings
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        send_mail(
            subject="Password Reset Request",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=None,
            recipient_list=[email],
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.contrib.auth.password_validation import validate_password
        try:
            uid = urlsafe_base64_decode(attrs['uid']).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid UID")

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError("Invalid or expired token")

        validate_password(attrs['new_password'], user)
        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user


class ReminderPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['reminder_mode', 'reminder_value']


class AvailableUnitsSerializer(serializers.ModelSerializer):
    landlord_id = serializers.CharField(source='property_obj.landlord.landlord_code', read_only=True)
    property_id = serializers.IntegerField(source='property_obj.id', read_only=True)
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    unit_number = serializers.CharField(read_only=True)

    class Meta:
        model = Unit
        fields = ['landlord_id', 'property_id', 'property_name', 'unit_number']
