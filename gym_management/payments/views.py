# payments/views.py

import json
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer
from activity_logs.utils import log_activity
from users.permissions import StaffOrAdmin, AdminOnly
from django.conf import settings


# -------------------------
# CRUD operations for Payments
# -------------------------
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        # Restrict creation to staff or admin only
        if not request.user.is_staff and getattr(request.user, "role", None) != "admin":
            return Response({"detail": "Only staff or admin can create payments."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        log_activity(
            user=request.user,
            action='PAYMENT_CREATED',
            target_type='payment',
            target_id=payment.id,
            metadata={
                'membership_id': getattr(payment.membership, 'id', None),
                'amount': str(payment.amount),
                'method': payment.method,
                'status': payment.status,
            },
            request=request
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """Members see only their own payments, staff/admin see all."""
        user = self.request.user
        if hasattr(user, "role") and user.role == 'member':
            return Payment.objects.filter(membership__user=user)
        return Payment.objects.all()


# -------------------------
# Chapa Integration Views
# -------------------------
def chapa_payment(request, payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return render(request, 'error.html', {'error': 'Payment not found'},
                      status=status.HTTP_404_NOT_FOUND)

    user = getattr(request, 'user', None)

    # ✅ Always ensure a valid email
    if user and getattr(user, 'is_authenticated', False) and user.email:
        email = user.email
    else:
        email = email = getattr(request.user, "email", None) or \
        getattr(payment.membership.user, "email", None) or \
        "portfolio_user@example.com"


    tx_ref = payment.tx_ref  # already generated in model.save()

    context = {
        'public_key': getattr(settings, "CHAPA_PUBLIC_KEY", "CHAPA_TEST_KEY"),
        'tx_ref': tx_ref,
        'amount': str(payment.amount),
        'email': email,  # ✅ safe email
        'first_name': getattr(user, "first_name", "Customer") if user else "Customer",
        'last_name': getattr(user, "last_name", "") if user else "",
        'title': f'Gym Membership Payment - {payment.membership.plan_type}',
        'description': f'Payment for {payment.membership.plan_type} membership',
        'callback_url': f'http://{request.get_host()}/api/payments/chapa/callback/',
        'return_url': f'http://{request.get_host()}/api/payments/success/',
        'payment_id': payment.id,
    }
    return render(request, 'payments/chapa.html', context)


# -------------------------
# Webhook (Chapa Callback)
# -------------------------
@csrf_exempt
def chapa_callback(request):
    """
    Minimal Chapa webhook for demo purposes.
    - Expects JSON body or form data containing 'tx_ref' and 'status'.
    - Marks payment as success if status indicates success.
    - Idempotent: if payment already success, returns 200.
    """
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST.dict()
    except Exception:
        payload = request.POST.dict()

    tx_ref = payload.get('tx_ref') or payload.get('txref') or payload.get('reference')
    status_str = (payload.get('status') or payload.get('payment_status') or '').lower()

    if not tx_ref:
        return JsonResponse({'detail': 'tx_ref missing'}, status=400)

    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
    except Payment.DoesNotExist:
        log_activity(user=None, action='SYSTEM_WEBHOOK_RECEIVED_UNKNOWN',
                     target_type='payment', target_id=None, metadata={'payload': payload})
        return JsonResponse({'detail': 'unknown tx_ref'}, status=200)

    # Idempotent check
    if payment.status == 'success':
        return JsonResponse({'detail': 'already processed'}, status=200)

    if status_str in ('success', 'completed', 'ok', 'paid'):
        with transaction.atomic():
            payment.status = 'success'
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at'])

            log_activity(
                user=None,
                action='PAYMENT_VERIFIED',
                target_type='payment',
                target_id=payment.id,
                metadata={'tx_ref': payment.tx_ref, 'amount': str(payment.amount), 'payload': payload},
                request=None
            )
        return JsonResponse({'detail': 'payment marked success'}, status=200)

    # Otherwise failed
    payment.status = 'failed'
    payment.save(update_fields=['status'])
    log_activity(user=None, action='PAYMENT_FAILED', target_type='payment',
                 target_id=payment.id, metadata={'payload': payload}, request=None)
    return JsonResponse({'detail': 'payment not successful'}, status=200)


# -------------------------
# Frontend result pages
# -------------------------
def payment_success(request):
    return render(request, 'payments/payment_success.html', status=200)


def payment_failure(request):
    return render(request, 'payments/payment_failure.html', status=400)
