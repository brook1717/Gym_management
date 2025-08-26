from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'membership', 'amount', 'method', 'paid_at']
        read_only_fields = ['id', 'paid_at']

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['membership', 'amount', 'method']