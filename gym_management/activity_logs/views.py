# activity_logs/views.py
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from users.permissions import AdminOnly  # assumes you have this permission as discussed
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class ActivityLogViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    """
    Admin-only listing and retrieval of activity logs.
    Supports simple filtering by user, action, target_type, target_id and date range.
    """
    queryset = ActivityLog.objects.all().select_related('user')
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, AdminOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'user', 'target_type', 'target_id']
    search_fields = ['metadata']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    # Optional: small override to allow staff later if you want to expand permissions
    # but keep AdminOnly for now (portfolio simplicity).
