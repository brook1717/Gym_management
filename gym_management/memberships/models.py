from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


#available membership plans
PLAN_CHOICES = [
    ('standard',  'Standard'),
    ('premium', 'Premium'),
    ('lifetime', 'Lifetime'),
]

class Membership(models.Model):
     #link membership to the user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships'  )
    plan_type= models.CharField(max_length=30, choices=PLAN_CHOICES)
    start_date = models.DateField(default=timezone.now)
    expiration_date=models.DateField()


    def save(self, *args, **kwargs):
        if not self.start_date:
            self.start_date = timezone.now().date()

             # Auto-calculate expiration date based on plan
        if self.plan_type == 'standard':
            self.expiration_date = self.start_date + timedelta(days=30)
        elif self.plan_type == 'premium':
            self.expiration_date = self.start_date + timedelta(days=90)

        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.user.full_name}  {self.plan_type.capitalize()} Plan"