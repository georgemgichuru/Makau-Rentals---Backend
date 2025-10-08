from django.db import models
from accounts.models import CustomUser, Unit

class Report(models.Model):
    ISSUE_CATEGORIES = [
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('noise', 'Noise'),
        ('safety/violence', 'Safety/Violence'),
        ('wifi', 'WiFi'),
        ('maintenance', 'Maintenance'),
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

    tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='reports')
    issue_category = models.CharField(max_length=20, choices=ISSUE_CATEGORIES)
    priority_level = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    issue_title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')

    def __str__(self):
        return f"Report by {self.tenant.full_name} - {self.issue_title}"
