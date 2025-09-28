from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app.tasks import notify_due_rent_task, landlord_summary_task


# ------------------------------
# MANUAL TRIGGER: Tenant Reminders
# ------------------------------
class TriggerTenantReminderView(APIView):
    """
    POST: Manually trigger tenant rent reminders (SMS + Email).
    Useful for testing or sending reminders outside the scheduled time.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        result = notify_due_rent_task.delay()  # Run asynchronously via Celery
        return Response({"message": "Tenant reminder task triggered", "task_id": result.id})


# ------------------------------
# MANUAL TRIGGER: Landlord Summaries
# ------------------------------
class TriggerLandlordSummaryView(APIView):
    """
    POST: Manually trigger landlord rent summary emails.
    Useful for testing or sending summaries outside the scheduled time.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        result = landlord_summary_task.delay()  # Run asynchronously via Celery
        return Response({"message": "Landlord summary task triggered", "task_id": result.id})
