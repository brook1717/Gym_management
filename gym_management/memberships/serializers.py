from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Membership
from dateutil.relativedelta import relativedelta

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
     




class MembershipUpdateSerializer(serializers.ModelSerializer):
    renew_months = serializers.IntegerField(min_value=1, max_value=36, required=False)
    force = serializers.BooleanField(default=False, required=False)
    
    class Meta:
        model = Membership
        fields = ['plan_type', 'start_date', 'renew_months', 'force']
        extra_kwargs = {
            'plan_type': {'required': False},
            'start_date': {'required': False}
        }
    
    def validate(self, data):
        membership = self.instance
        request = self.context.get('request')
        
        # Check if changing from lifetime plan
        if membership.plan_type == 'lifetime' and 'plan_type' in data and data['plan_type'] != 'lifetime':
            if not (data.get('force') and request.user.role == 'admin'):
                raise serializers.ValidationError("Cannot change from lifetime plan without admin override")
        
        # Validate start date
        if 'start_date' in data and data['start_date'] < timezone.now().date():
            if not (data.get('force') and request.user.role == 'admin'):
                raise serializers.ValidationError("Cannot set start date in the past without admin override")
        
        return data
    
    def update(self, instance, validated_data):
        renew_months = validated_data.pop('renew_months', None)
        force = validated_data.pop('force', False)
        
        # Handle plan type change
        if 'plan_type' in validated_data:
            instance.plan_type = validated_data['plan_type']
        
        # Handle start date change
        if 'start_date' in validated_data:
            instance.start_date = validated_data['start_date']
        
        # Calculate expiry date based on business rules
        instance.expiration_date = self.calculate_expiration_date(instance, renew_months)
        
        instance.save()
        return instance
    
    def calculate_expiration_date(self, membership, renew_months=None):
        today = timezone.now().date()
        
        
        if membership.plan_type == 'lifetime':
            return None
    
    # Determine renewal period
        if renew_months:
            months = renew_months
        else:
            months = 3 if membership.plan_type == 'premium' else 1
            
        start_date = membership.start_date if membership.start_date else today
        
        
        new_expiry = start_date + relativedelta(months=+months)
       
       
       
        if membership.expiration_date and membership.expiration_date >= today:
            new_expiry = membership.expiration_date + relativedelta(months=+months)
    
        return new_expiry