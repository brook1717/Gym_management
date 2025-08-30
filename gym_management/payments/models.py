from django.db import models
from django.utils import timezone
import uuid

class Payment(models.Model):
    #available payment methods
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'Mobile'),
        ('chapa', 'Chapa'),
    ]
    #status of the payment
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    #link payment to a membership
    membership = models.ForeignKey('memberships.Membership', on_delete=models.CASCADE)
    #payment amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    #Chosen payment method
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='chapa')
    #current status of the payment
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    tx_ref = models.CharField(max_length=100, unique=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.tx_ref:
            self.tx_ref = f"gym-{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)


    chapa_transaction_id = models.CharField(max_length=100, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField( default=timezone.now)
    
    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ({self.status})"