from django.shortcuts import render, redirect
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer
import uuid
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(PaymentSerializer(payment).data, status=201)

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "role") and user.role == 'member':
            return Payment.objects.filter(membership__user=user)
        return Payment.objects.all()

# Chapa Integration Views
def chapa_payment(request, payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
        tx_ref = payment.tx_ref  # already generated in model.save()

        context = {
            'public_key': 'CHAPUBK_TEST-XXXXXX',  
            'tx_ref': tx_ref,
            'amount': str(payment.amount),
            'email': request.user.email,
            'first_name': request.user.first_name or 'Customer',
            'last_name': request.user.last_name or '',
            'title': f'Gym Membership Payment - {payment.membership.plan_type}',
            'description': f'Payment for {payment.membership.plan_type} membership',
            'callback_url': f'http://{request.get_host()}/payments/chapa/callback/',
            'return_url': f'http://{request.get_host()}/payments/success/',
            'payment_id': payment.id,  # <-- ✅ add this
        }
        return render(request, 'chapa.html', context)

    except Payment.DoesNotExist:
        return render(request, 'error.html', {'error': 'Payment not found'})


def chapa_callback(request):
    # Handle Chapa payment callback (webhook)
    # Verify payment status and update your database
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')
    
    # Update payment status based on Chapa response
    # You'll need to implement proper verification here
    
    return Response({'status': 'received'})

def payment_success(request):
    return render(request, 'payment_success.html')

def payment_failure(request):
    return render(request, 'payment_failure.html')