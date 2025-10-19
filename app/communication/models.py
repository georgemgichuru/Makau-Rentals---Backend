from django.db import models
from accounts.models import CustomUser, Unit
from django.utils import timezone

from django.db import models
from accounts.models import CustomUser, Unit
from django.utils import timezone

class Report(models.Model):
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

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    # Basic required fields
    tenant = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='reports',
        limit_choices_to={'user_type': 'tenant'}
    )
    unit = models.ForeignKey(
        Unit, 
        on_delete=models.CASCADE, 
        related_name='reports'
    )
    issue_category = models.CharField(max_length=20, choices=ISSUE_CATEGORIES)
    priority_level = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    issue_title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')

    # Additional fields you added
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
    
    # File attachments
    attachment = models.FileField(upload_to='report_attachments/', null=True, blank=True)
    
    class Meta:
        ordering = ['-reported_date']
        verbose_name = 'Maintenance Report'
        verbose_name_plural = 'Maintenance Reports'

    def save(self, *args, **kwargs):
        # Auto-assign priority based on category if not set
        if not self.priority_level or self.priority_level == 'medium':
            urgent_categories = ['safety', 'electrical', 'plumbing', 'security']
            self.priority_level = 'urgent' if self.issue_category in urgent_categories else 'medium'
        
        # Auto-set resolved_date when status changes to resolved
        if self.status == 'resolved' and not self.resolved_date:
            self.resolved_date = timezone.now()
        elif self.status != 'resolved' and self.resolved_date:
            self.resolved_date = None
            
        super().save(*args, **kwargs)

    @property
    def days_open(self):
        """Calculate how many days the report has been open"""
        if self.status == 'resolved' and self.resolved_date:
            return (self.resolved_date - self.reported_date).days
        return (timezone.now() - self.reported_date).days

    @property
    def is_urgent(self):
        """Check if the report is urgent based on priority and days open"""
        return self.priority_level == 'urgent' or self.days_open > 7

    def __str__(self):
        return f"Report #{self.id} - {self.issue_title} ({self.tenant.full_name})"