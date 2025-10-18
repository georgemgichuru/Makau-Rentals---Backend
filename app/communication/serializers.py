from rest_framework import serializers
from .models import Report
from accounts.models import CustomUser, Unit, Property

class ReportSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property_obj.name', read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'tenant', 'tenant_name', 'unit', 'unit_number', 'property_name',
            'issue_category', 'priority_level', 'issue_title', 'description',
            'status', 'reported_date', 'resolved_date', 'assigned_to',
            'estimated_cost', 'actual_cost', 'attachment', 'days_open'
        ]
        read_only_fields = ['tenant', 'reported_date', 'days_open']

    def validate(self, data):
        # Ensure tenants can only report issues for their own units
        if self.instance and self.instance.tenant != self.context['request'].user:
            raise serializers.ValidationError("You can only modify your own reports")
        return data

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
