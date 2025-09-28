# activity_logs/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

# Use Django's JSONField (works with Postgres JSONB and falls back on Text for SQLite)
try:
    from django.db.models import JSONField  # Django >= 3.1
except Exception:
    from django.contrib.postgres.fields import JSONField  # fallback for older setups

class ActivityLog(models.Model):
    """
    Lightweight activity log for auditing.
    """
    ACTION_MAX_LEN = 100
    TARGET_TYPE_MAX_LEN = 50
    TARGET_ID_MAX_LEN = 64

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=ACTION_MAX_LEN)
    target_type = models.CharField(max_length=TARGET_TYPE_MAX_LEN, null=True, blank=True)
    target_id = models.CharField(max_length=TARGET_ID_MAX_LEN, null=True, blank=True)
    metadata = JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self):
        return f"[{self.created_at.isoformat()}] {self.action} by {self.user or 'system'}"
