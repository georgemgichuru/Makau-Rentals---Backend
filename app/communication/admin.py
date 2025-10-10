from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'unit', 'issue_category', 'priority_level', 'issue_title', 'status', 'created_at')
    list_filter = ('issue_category', 'priority_level', 'status', 'created_at')
    search_fields = ('tenant__full_name', 'unit__unit_number', 'issue_title', 'description')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'tenant',
            'unit',
            'unit__property_obj',
            'unit__property_obj__landlord'
        ).defer(
            'tenant__password',
            'tenant__government_id',
            'tenant__id_document',
            'unit__property_obj__landlord__password',
            'unit__property_obj__landlord__government_id',
            'unit__property_obj__landlord__id_document',
        )
