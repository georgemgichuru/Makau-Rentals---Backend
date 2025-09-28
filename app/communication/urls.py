from django.urls import path
from .views import (
    TriggerTenantReminderView,
    TriggerLandlordSummaryView,
)

urlpatterns = [
    # ------------------------------
    # CELERY TASK TRIGGERS
    # ------------------------------
    path("tasks/trigger/tenant-reminders/", TriggerTenantReminderView.as_view(), name="trigger-tenant-reminders"),
    path("tasks/trigger/landlord-summaries/", TriggerLandlordSummaryView.as_view(), name="trigger-landlord-summaries"),
]
