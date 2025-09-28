# activity_logs/serializers.py
from rest_framework import serializers
from .models import ActivityLog
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class ActivityUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class ActivityLogSerializer(serializers.ModelSerializer):
    user = ActivityUserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            'id', 'user', 'action', 'target_type', 'target_id',
            'metadata', 'ip_address', 'user_agent', 'created_at'
        )
        read_only_fields = fields
