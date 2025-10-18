from django.db import models
from accounts.models import CustomUser, Unit
from django.utils import timezone

class Report(models.Model):
    # Add more categories
    ISSUE_CATEGORIES = [
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('noise', 'Noise'),
        ('safety', 'Safety/Violence'),
        ('wifi', 'WiFi'),
        ('maintenance', 'General Maintenance'),
        ('pest', 'Pest Control'),
        ('security', 'Security'),
        ('cleanliness', 'Cleanliness'),
        ('other', 'Other'),
    ]

    # Add these fields for better tracking
    reported_date = models.DateTimeField(auto_now_add=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'user_type': 'landlord'},
        related_name='assigned_reports'
    )
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Add file attachments
    attachment = models.FileField(upload_to='report_attachments/', null=True, blank=True)
    
    # Add priority auto-assignment
    def save(self, *args, **kwargs):
        # Auto-assign priority based on category
        if not self.priority_level:
            urgent_categories = ['safety', 'electrical', 'plumbing']
            self.priority_level = 'urgent' if self.issue_category in urgent_categories else 'medium'
        super().save(*args, **kwargs)

    @property
    def days_open(self):
        if self.status == 'resolved' and self.resolved_date:
            return (self.resolved_date - self.reported_date).days
        return (timezone.now() - self.reported_date).days
