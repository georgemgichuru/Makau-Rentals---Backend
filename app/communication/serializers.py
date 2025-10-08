from rest_framework import serializers
from .models import Report
from accounts.models import CustomUser, Unit, Property

class ReportSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all())

    class Meta:
        model = Report
        fields = [
            'id',
            'tenant',
            'unit',
            'issue_category',
            'priority_level',
            'issue_title',
            'description',
            'created_at',
            'status',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'status']

    def validate_unit(self, value):
        # Ensure the unit belongs to the tenant submitting the report
        user = self.context['request'].user
        if value.tenant != user:
            raise serializers.ValidationError("This unit is not assigned to the current tenant.")
        return value

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user
        return super().create(validated_data)

class UpdateReportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['status']
        read_only_fields = []

class SendEmailSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    tenants = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(user_type='tenant')),
        required=False,
        allow_empty=True
    )
    send_to_all = serializers.BooleanField(default=False)

    def validate(self, data):
        if not data.get('send_to_all') and not data.get('tenants'):
            raise serializers.ValidationError("Either provide a list of tenants or set send_to_all to True.")
        if data.get('send_to_all') and data.get('tenants'):
            raise serializers.ValidationError("Cannot specify tenants when send_to_all is True.")
        return data

    def validate_tenants(self, value):
        # Ensure all tenants belong to the landlord's properties
        request = self.context.get('request')
        if request and request.user.user_type == 'landlord':
            landlord_properties = Property.objects.filter(landlord=request.user)
            tenant_units = Unit.objects.filter(property_obj__in=landlord_properties, tenant__in=value)
            valid_tenants = set(tenant_units.values_list('tenant', flat=True))
            if set(t.id for t in value) != valid_tenants:
                raise serializers.ValidationError("Some tenants do not belong to your properties.")
        return value
