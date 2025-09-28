# services/messaging.py
import africastalking
from django.conf import settings
from django.core.mail import send_mail

def send_bulk_emails(tenants):
    for tenant in tenants:
        subject = "Rent Payment Reminder"
        message = f"Hello {tenant.name},\n\nThis is a reminder to pay your rent.\nOutstanding balance: KES {tenant.balance}."
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [tenant.email])
        except Exception as e:
            print(f"Email failed for {tenant.email}: {e}")


# Initialize Africa's Talking
africastalking.initialize(
    username=settings.AT_USERNAME,
    api_key=settings.AT_API_KEY
)
sms = africastalking.SMS

def send_bulk_sms(tenants):
    messages = []
    for tenant in tenants:
        message = f"Hello {tenant.name}, kindly pay your rent. Outstanding balance: KES {tenant.balance}."
        messages.append((tenant.phone_number, message))

    for phone, msg in messages:
        try:
            response = sms.send(msg, [phone], sender_id=settings.AT_SENDER_ID)
            print(response)
        except Exception as e:
            print(f"SMS failed for {phone}: {e}")
            
# Function to notify all tenants (example usage)
def notify_tenants():
    from .models import Tenant
    tenants = Tenant.objects.all()
    send_bulk_sms(tenants)
    send_bulk_emails(tenants)

# TODO: This is for sending bulk emails and SMS to tenants for rent reminders