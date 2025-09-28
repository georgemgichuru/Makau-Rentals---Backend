# app/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from accounts.models import Unit, CustomUser
from communication.messaging import send_bulk_sms, send_bulk_emails
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def notify_due_rent_task():
    """
    Celery task to notify tenants whose rent is due today or overdue.
    """
    today = timezone.now().date()
    due_units = Unit.objects.filter(
        tenant__isnull=False,
        rent_due_date__lte=today,
        rent_remaining__gt=0
    )
    tenants = [u.tenant for u in due_units if u.tenant]

    if tenants:
        send_bulk_sms(tenants)
        send_bulk_emails(tenants)

    return f"Notified {len(tenants)} tenants with due/overdue rent"


@shared_task
def landlord_summary_task():
    """
    Celery task to send landlords a summary of tenants with due/overdue rent.
    Runs daily (or weekly if you prefer).
    """
    today = timezone.now().date()
    landlords = CustomUser.objects.filter(user_type="landlord")

    for landlord in landlords:
        # Get all units owned by this landlord
        units = Unit.objects.filter(property__landlord=landlord)

        # Filter tenants who are due/overdue
        overdue_units = units.filter(
            tenant__isnull=False,
            rent_due_date__lte=today,
            rent_remaining__gt=0
        )

        if not overdue_units.exists():
            continue  # Skip landlords with no overdue tenants

        # Build summary message
        summary_lines = []
        total_outstanding = 0
        for unit in overdue_units:
            tenant = unit.tenant
            summary_lines.append(
                f"Unit {unit.unit_number} - Tenant: {tenant.first_name} {tenant.last_name} "
                f"({tenant.email}) | Due: {unit.rent_due_date} | Outstanding: KES {unit.rent_remaining}"
            )
            total_outstanding += float(unit.rent_remaining)

        subject = "Daily Rent Summary - Overdue Tenants"
        message = (
            f"Hello {landlord.first_name},\n\n"
            f"Here is the summary of overdue tenants in your properties:\n\n"
            + "\n".join(summary_lines)
            + f"\n\nTotal Outstanding: KES {total_outstanding}\n\n"
            "Regards,\nYour Rental Management System"
        )

        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [landlord.email])
        except Exception as e:
            print(f"Failed to send summary to {landlord.email}: {e}")

    return "Landlord summaries sent"
