from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Membership

class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    class Meta:
        model = Membership
        fields =  ['id',
            'user',
            'user_email',
            'user_name',
            'plan_type',
            'start_date',
            'expiration_date',
            'is_active']
        read_only_fields = ['id', 'expiration_date', 'is_active']


class MembershipCreateSerializer(serializers.ModelSerializer):
     user_id = serializers.IntegerField(write_only=True)
    
     class Meta:
        model = Membership
        fields = ['user_id', 'plan_type', 'start_date']
        extra_kwargs = {
            'start_date': {'required': False},
            'plan_type': {'required': True}
        }
    
     def validate_user_id(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value
    
     def validate_start_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Start date cannot be in the past")
        return value or timezone.now().date()
    
     def validate(self, data):
        user_id = data['user_id']
        start_date = data.get('start_date', timezone.now().date())
        

        if Membership.objects.filter(user_id=user_id, expiration_date__gte=timezone.now().date()).exists():
            raise serializers.ValidationError("User already has an active membership")
        
        plan_type = data['plan_type']
        if plan_type == 'standard':
            data['expiration_date'] = start_date + timedelta(days=30)
        elif plan_type == 'premium':
            data['expiration_date'] = start_date + timedelta(days=90)
        elif plan_type == 'lifetime':
            data['expiration_date'] = datetime(2099, 12, 31).date()
        else:
            raise serializers.ValidationError("Invalid plan type")
        
        return data
    
     def create(self, validated_data):

        user_id = validated_data.pop('user_id')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        return Membership.objects.create(user=user, **validated_data)