from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, chapa_payment, chapa_callback, payment_success, payment_failure

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = [
   
    path('chapa/<int:payment_id>/', chapa_payment, name='chapa-payment'),
    path('chapa/callback/', chapa_callback, name='chapa-callback'),
    path('success/', payment_success, name='payment-success'),
    path('failure/', payment_failure, name='payment-failure'),
    path('', include(router.urls)),
]
