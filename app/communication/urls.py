from django.urls import path
from .views import (
    CreateReportView,
    OpenReportsView,
    UrgentReportsView,
    InProgressReportsView,
    ResolvedReportsView,
    UpdateReportStatusView,
    SendEmailView,
)

urlpatterns = [
    # Create a new report (POST)
    path('reports/create/', CreateReportView.as_view(), name='create-report'),  # Added /create/

    # List open reports for the authenticated user (GET)
    path('reports/open/', OpenReportsView.as_view(), name='open-reports'),

    # List urgent reports for the authenticated user (GET)
    path('reports/urgent/', UrgentReportsView.as_view(), name='urgent-reports'),

    # List in-progress reports for the authenticated user (GET)
    path('reports/in-progress/', InProgressReportsView.as_view(), name='in-progress-reports'),

    # List resolved reports for the authenticated user (GET)
    path('reports/resolved/', ResolvedReportsView.as_view(), name='resolved-reports'),

    # Update the status of a specific report (PATCH/PUT)
    path('reports/<int:pk>/update-status/', UpdateReportStatusView.as_view(), name='update-report-status'),

    # Send email to tenants (POST)
    path('reports/send-email/', SendEmailView.as_view(), name='send-email'),  # Added /reports/ prefix
]