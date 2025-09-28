import os
from celery import Celery   # <-- FIX: import from celery package, not app.app.celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
