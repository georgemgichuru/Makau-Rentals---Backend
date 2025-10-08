# services/messaging.py
from django.conf import settings
from django.core.mail import send_mail


def send_bulk_emails(tenants):
    """
    Send rent reminder emails to a list of tenants.
    Each tenant receives a personalized message with their outstanding balance.
    """
    for tenant in tenants:
        subject = "Rent Payment Reminder"
        message = (
            f"Hello {tenant.full_name},\n\n"
            f"This is a reminder to pay your rent.\n"
            f"Outstanding balance: KES {tenant.unit.rent_remaining}."
        )
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [tenant.email])
        except Exception as e:
            print(f"Email failed for {tenant.email}: {e}")





def send_deadline_reminder_emails(tenants):
    """
    Send rent deadline reminder emails to a list of tenants.
    Each email includes the payment deadline date, outstanding balance, and login link.
    """
    for tenant in tenants:
        unit = tenant.unit
        subject = "Rent Payment Deadline Reminder"
        login_link = f"{settings.FRONTEND_URL}/login"
        message = (
            f"Hello {tenant.full_name},\n\n"
            f"This is a reminder that your rent payment is due on {unit.rent_due_date}.\n"
            f"Outstanding balance: KES {unit.rent_remaining}.\n\n"
            f"Please log in to your account to make the payment: {login_link}\n\n"
            "Thank you,\n"
            "Makau Rentals Team"
        )
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [tenant.email])
        except Exception as e:
            print(f"Email failed for {tenant.email}: {e}")


def send_deadline_reminders():
    """
    Send reminders to tenants whose rent payment deadline is 10 days away.
    """
    from datetime import timedelta
    from django.utils import timezone
    from accounts.models import CustomUser

    reminder_date = timezone.now().date() + timedelta(days=10)
    tenants = CustomUser.objects.filter(
        user_type="tenant",
        unit__isnull=False,
        unit__rent_due_date=reminder_date,
        unit__rent_remaining__gt=0
    )

    if tenants:
        send_deadline_reminder_emails(tenants)

# TODO:
# - This module handles sending bulk emails to tenants for rent reminders.
# - It uses Django's send_mail for email notifications.
# - The send_deadline_reminders() function is scheduled via Celery Beat to run automatically.

def send_report_email(report):
    """
    Send an email to the landlord when a new report is created.
    """
    landlord = report.unit.property_obj.landlord
    subject = f"New Issue Report: {report.issue_title}"
    issue_url = f"{settings.FRONTEND_URL}/reports/{report.id}"
    message = (
        f"Hello {landlord.full_name},\n\n"
        f"A new issue report has been submitted by tenant {report.tenant.full_name}.\n\n"
        f"Unit Number: {report.unit.unit_number}\n"
        f"Issue Category: {report.issue_category}\n"
        f"Priority Level: {report.priority_level}\n"
        f"Issue Title: {report.issue_title}\n"
        f"Description:\n{report.description}\n\n"
        f"To resolve the issue, please visit: {issue_url}\n\n"
        "Best regards,\n"
        "Makau Rentals System"
    )
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [landlord.email])
    except Exception as e:
        print(f"Failed to send report email: {e}")


def send_landlord_email(subject, message, tenants):
    """
    Send a custom email from landlord to a list of tenants.
    """
    recipient_emails = [tenant.email for tenant in tenants]
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_emails)
    except Exception as e:
        print(f"Failed to send landlord email: {e}")
