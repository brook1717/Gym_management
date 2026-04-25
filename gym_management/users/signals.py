from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_member_profile(sender, instance, created, **kwargs):
    if created and instance.role == 'member':
        from .models import MemberProfile
        MemberProfile.objects.create(user=instance)
