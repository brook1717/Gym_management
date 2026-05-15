"""
Celery application configuration for the Gym Management project.

In production (Docker / AWS):
  - Broker and result backend use Redis (ElastiCache).
  - Workers are started via the celery_worker service in docker-compose.yml.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gym_management.settings")

app = Celery("gym_management")

# Read config from Django settings, prefixed with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()
