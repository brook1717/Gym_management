from django.db import models
from django.conf import settings
from django.utils import timezone


class Document(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/%Y/%m/')
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} — {self.member.full_name}"
