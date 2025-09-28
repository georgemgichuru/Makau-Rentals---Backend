# services/messaging.py
import africastalking
from django.conf import settings
from django.core.mail import send_mail

# ------------------------------
# Initialize Africa's Talking SDK
# ------------------------------
africastalking.initialize(
    username=settings.AT_USERNAME,
    api_key=settings.AT_API_KEY
)
sms = africastalking.SMS


def send_bulk_emails(tenants):
    """
    Send rent reminder emails to a list of tenants.
    Each tenant receives a personalized message with their outstanding balance.
    """
    for tenant in tenants:
        subject = "Rent Payment Reminder"
        message = (
            f"Hello {tenant.first_name},\n\n"
            f"This is a reminder to pay your rent.\n"
            f"Outstanding balance: KES {tenant.unit.rent_remaining}."
        )
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [tenant.email])
        except Exception as e:
            print(f"Email failed for {tenant.email}: {e}")


def send_bulk_sms(tenants):
    """
    Send rent reminder SMS to a list of tenants.
    Uses Africa's Talking SMS gateway.
    """
    for tenant in tenants:
        message = (
            f"Hello {tenant.first_name}, kindly pay your rent. "
            f"Outstanding balance: KES {tenant.unit.rent_remaining}."
        )
        try:
            response = sms.send(message, [tenant.phone_number], sender_id=settings.AT_SENDER_ID)
            print(response)
        except Exception as e:
            print(f"SMS failed for {tenant.phone_number}: {e}")


def notify_tenants():
    """
    Notify all tenants with outstanding balances via SMS and Email.
    This function is called by the Celery task on schedule.
    """
    from accounts.models import CustomUser
    tenants = CustomUser.objects.filter(user_type="tenant", unit__isnull=False)

    # Only notify tenants who actually owe rent
    tenants = [t for t in tenants if t.unit and t.unit.rent_remaining > 0]

    send_bulk_sms(tenants)
    send_bulk_emails(tenants)

# TODO:
# - This module handles sending bulk emails and SMS to tenants for rent reminders.
# - It integrates with Africa's Talking for SMS and Django's send_mail for email.
# - The notify_tenants() function is scheduled via Celery Beat to run automatically.
