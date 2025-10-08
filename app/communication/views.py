from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Report
from .serializers import ReportSerializer, UpdateReportStatusSerializer, SendEmailSerializer
from accounts.permissions import CanAccessReport, IsTenant, IsLandlord
from accounts.models import CustomUser, Unit
from .messaging import send_landlord_email

class CreateReportView(generics.CreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        report = serializer.save()
        # Import here to avoid circular imports
        from app.app.tasks import send_report_email_task
        send_report_email_task.delay(report.id)

class OpenReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Report.objects.filter(tenant=user, status='open')
        elif user.user_type == 'landlord':
            return Report.objects.filter(unit__property__landlord=user, status='open')
        return Report.objects.none()

class UrgentReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Report.objects.filter(tenant=user, priority_level='urgent')
        elif user.user_type == 'landlord':
            return Report.objects.filter(unit__property__landlord=user, priority_level='urgent')
        return Report.objects.none()

class InProgressReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Report.objects.filter(tenant=user, status='in_progress')
        elif user.user_type == 'landlord':
            return Report.objects.filter(unit__property__landlord=user, status='in_progress')
        return Report.objects.none()

class ResolvedReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'tenant':
            return Report.objects.filter(tenant=user, status='resolved')
        elif user.user_type == 'landlord':
            return Report.objects.filter(unit__property__landlord=user, status='resolved')
        return Report.objects.none()

class UpdateReportStatusView(generics.UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = UpdateReportStatusSerializer
    permission_classes = [permissions.IsAuthenticated, CanAccessReport]

class SendEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsLandlord]

    def post(self, request):
        serializer = SendEmailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            send_to_all = serializer.validated_data['send_to_all']

            if send_to_all:
                # Get all tenants of the landlord
                landlord_properties = request.user.property_set.all()
                tenants = CustomUser.objects.filter(
                    user_type='tenant',
                    unit__property_obj__in=landlord_properties
                ).distinct()
            else:
                tenants = serializer.validated_data['tenants']

            send_landlord_email(subject, message, tenants)
            return Response({"message": "Emails sent successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
