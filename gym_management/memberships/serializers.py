from rest_framework import serializers
from .models import Membership

class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Membership
        fields =  ['id',
            'user',
            'user_email',
            'user_name',
            'plan_type',
            'start_date',
            'expiry_date',
            'is_active']