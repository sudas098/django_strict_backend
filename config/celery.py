import os

from celery import Celery  # type: ignore[import-untyped]

# Set default Django settings module for celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Pull celery configurations prefixed with CELERY_ from settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py across all registered INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True)  # type: ignore[misc]
def debug_task(self: object) -> None:
    print(f"Request: {self.request!r}")  # type: ignore[attr-defined]
