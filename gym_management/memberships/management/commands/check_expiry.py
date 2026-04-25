from django.core.management.base import BaseCommand
from django.utils import timezone
from memberships.models import Membership
from activity_logs.utils import log_activity


class Command(BaseCommand):
    help = 'Check all memberships and mark expired ones where expiration_date has passed.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        expired_qs = Membership.objects.filter(
            expiration_date__lt=today,
            is_expired=False,
        )

        count = expired_qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No newly expired memberships found.'))
            return

        for membership in expired_qs.iterator():
            membership.is_expired = True
            membership.save(update_fields=['is_expired'])

            log_activity(
                user=None,
                action='MEMBERSHIP_EXPIRED',
                target_type='membership',
                target_id=membership.id,
                metadata={
                    'member_id': membership.user.id,
                    'member_name': membership.user.full_name,
                    'plan_type': membership.plan_type,
                    'expiration_date': str(membership.expiration_date),
                },
            )

            self.stdout.write(
                f'  Expired: {membership.user.full_name} — '
                f'{membership.plan_type} (expired {membership.expiration_date})'
            )

        self.stdout.write(self.style.SUCCESS(f'Marked {count} membership(s) as expired.'))
