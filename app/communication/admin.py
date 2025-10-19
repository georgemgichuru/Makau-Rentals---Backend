from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'tenant_name', 
        'unit_number', 
        'issue_category', 
        'priority_level', 
        'issue_title', 
        'status', 
        'reported_date'  # Changed from 'created_at' to 'reported_date'
    ]
    
    list_filter = [
        'issue_category', 
        'priority_level', 
        'status', 
        'reported_date'  # Changed from 'created_at' to 'reported_date'
    ]
    
    search_fields = [
        'issue_title', 
        'description', 
        'tenant__full_name',
        'unit__unit_number'
    ]
    
    readonly_fields = ['reported_date']  # Changed from 'created_at' to 'reported_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'unit', 'issue_category', 'priority_level')
        }),
        ('Issue Details', {
            'fields': ('issue_title', 'description', 'status')
        }),
        ('Additional Information', {
            'fields': ('assigned_to', 'estimated_cost', 'actual_cost', 'attachment')
        }),
        ('Timestamps', {
            'fields': ('reported_date', 'resolved_date'),  # Changed from 'created_at' to 'reported_date'
            'classes': ('collapse',)
        }),
    )
    
    # Custom methods for list_display
    def tenant_name(self, obj):
        return obj.tenant.full_name if obj.tenant else 'No Tenant'
    tenant_name.short_description = 'Tenant Name'
    
    def unit_number(self, obj):
        return obj.unit.unit_number if obj.unit else 'No Unit'
    unit_number.short_description = 'Unit Number'