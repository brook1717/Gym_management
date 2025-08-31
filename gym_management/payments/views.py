from django.shortcuts import render, redirect
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer
from django.http import JsonResponse

#CRUD operation for Payments
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]

      #use different serializer for creation
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    #custom create with explicit 201 response
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
    
     #restrict members to see only their own payments
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
            'public_key': 'CHAPUBK_TEST-tVCPOaCbJz1qHETIJinaXc3x9IJoAst4',  
            'tx_ref': tx_ref,
            'amount': str(payment.amount),
            'email': f"{request.user.phone_number}@gmail.com",
            'first_name': request.user.full_name or 'Customer',
            'last_name': '',
            'title': f'Gym Membership Payment - {payment.membership.plan_type}',
            'description': f'Payment for {payment.membership.plan_type} membership',
            'callback_url': f'http://{request.get_host()}/api/payments/chapa/callback/',
            'return_url': f'http://{request.get_host()}/api/payments/success/',
            'payment_id': payment.id
        }
        return render(request, 'payments/chapa.html', context)

    except Payment.DoesNotExist:
        return render(request, 'error.html', {'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

#Webhook for Chapa payment callback
def chapa_callback(request):
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')
    
    
    return JsonResponse({'status': 'received'}, status=200)
def payment_success(request):
    return render(request, 'payments/payment_success.html', status=200)
def payment_failure(request):
    return render(request, 'payments/payment_failure.html',status=400)