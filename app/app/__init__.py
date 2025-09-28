from .celery_app import app as celery_app

__all__ = ("celery_app",)
# This makes sure the app is always imported when
# Django starts so that shared tasks use this app.  