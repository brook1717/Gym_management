from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MembershipViewSet, MembershipUpdateView

router = DefaultRouter()

router.register(r'', MembershipViewSet, basename='membership')


urlpatterns = [
    path('', include(router.urls)),
    path('memberships/<int:pk>/', MembershipUpdateView.as_view(), name='membership-update'),
]