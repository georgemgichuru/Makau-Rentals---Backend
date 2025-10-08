# app/tasks.py
from celery import shared_task
from communication.messaging import send_report_email

@shared_task
def send_report_email_task(report_id):
    from communication.models import Report
    try:
        report = Report.objects.get(id=report_id)
        send_report_email(report)
    except Report.DoesNotExist:
        print(f"Report with id {report_id} does not exist.")
from django.utils import timezone
from datetime import timedelta
from accounts.models import Unit, CustomUser
from payments.models import Payment
from communication.messaging import send_bulk_emails
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
        units = Unit.objects.filter(property_obj__landlord=landlord)

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
                f"Unit {unit.unit_number} - Tenant: {tenant.full_name} "
                f"({tenant.email}) | Due: {unit.rent_due_date} | Outstanding: KES {unit.rent_remaining}"
            )
            total_outstanding += float(unit.rent_remaining)

        subject = "Daily Rent Summary - Overdue Tenants"
        message = (
            f"Hello {landlord.full_name},\n\n"
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


@shared_task
def delete_unpaid_deposit_tenants():
    """
    Celery task to delete tenants who haven't paid deposit within 14 days of assignment.
    """
    now = timezone.now()
    cutoff_date = now - timedelta(days=14)
    units = Unit.objects.filter(
        tenant__isnull=False,
        assigned_date__isnull=False,
        assigned_date__lte=cutoff_date
    )
    deleted_count = 0
    for unit in units:
        tenant = unit.tenant
        # Check if there is a successful deposit payment within 14 days
        deposit_deadline = unit.assigned_date + timedelta(days=14)
        has_deposit = Payment.objects.filter(
            tenant=tenant,
            payment_type='deposit',
            status='Success',
            transaction_date__lte=deposit_deadline
        ).exists()
        if not has_deposit:
            tenant.delete()
            deleted_count += 1
    return f"Deleted {deleted_count} tenants for unpaid deposit"


@shared_task
def delete_left_tenants():
    """
    Celery task to delete tenants who have been out of a unit for 7 days.
    """
    now = timezone.now()
    cutoff_date = now - timedelta(days=7)
    units = Unit.objects.filter(
        left_date__isnull=False,
        left_date__lte=cutoff_date
    )
    deleted_count = 0
    for unit in units:
        if unit.tenant:  # Though it should be None, but to be safe
            unit.tenant.delete()
            deleted_count += 1
    return f"Deleted {deleted_count} tenants who left units"


@shared_task
def deadline_reminder_task():
    """
    Celery task to send reminders to tenants whose rent payment deadline is 10 days away.
    """
    from communication.messaging import send_deadline_reminders
    send_deadline_reminders()
    return "Deadline reminders sent"
