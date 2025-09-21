from auth.models import User
from django.core import serializers
from django.contrib.auth.models import Permission

# User model serializer that ensures a a user is assigned to only one role
class User_Serializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'government_id', 'emergency_contact', 'is_active', 'is_staff',
            'date_joined', 'tenant', 'landlord'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff']

    def validate(self, attrs):
        tenant = attrs.get('tenant', False)
        landlord = attrs.get('landlord', False)

        if tenant and landlord:
            raise serializers.ValidationError("A user cannot be both a tenant and a landlord.")
        if not tenant and not landlord:
            raise serializers.ValidationError("A user must be either a tenant or a landlord.")

        return attrs

# Assign the landlord specific permissions custom to it
def assign_landlord_permissions(User):
    if User.landlord:
        perms = Permission.objects.filter(codename__in=[
            'can_approve_rentals',
            'can_edit_building',
            'can_edit_unit',
            'can_view_unit',
        ])
        User.user_permissions.set(perms)

# Assign the tenant specific permissions custom to it
def assign_tenant_permissions(User):
        if User.tenant:
            perms = Permission.objects.filter(codename__in=[
                'can_view_unit',
            ])
            User.user_permissions.set(perms)