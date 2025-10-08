from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'unit', 'issue_category', 'priority_level', 'issue_title', 'status', 'created_at')
    list_filter = ('issue_category', 'priority_level', 'status', 'created_at')
    search_fields = ('tenant__full_name', 'unit__unit_number', 'issue_title', 'description')
    readonly_fields = ('created_at',)
