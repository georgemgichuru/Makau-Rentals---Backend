# app/tasks.py
from celery import shared_task
from .services.messaging import send_bulk_sms, send_bulk_emails
from .models import Tenant

@shared_task
def notify_tenants_task():
    tenants = Tenant.objects.all()
    send_bulk_sms(tenants)
    send_bulk_emails(tenants)
# Task to notify all tenants via SMS and email