from django.db import models
from django.conf import settings


PLAN_CHOICES = [
    ('standard',  'Standard'),
    ('premium', 'Premium'),
    ('lifetime', 'Lifetime'),
]

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships'  )
    plan_type= models.CharField(max_length=30, choices=PLAN_CHOICES)
    start_date = models.DateField(auto_now_add=True)
    expiration_date=models.DateField()



    def __str__(self):
        return f"{self.user.name} The plan type is:  {self.plan_type}"