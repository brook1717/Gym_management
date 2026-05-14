from rest_framework import serializers
from users.models import User


class Users_serializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'role', 'is_verified',
            'mfa_enabled', 'oauth_provider', 'profile_image',
            'phone_number', 'created_at', 'last_login',
        ]
        read_only_fields = ['id', 'role', 'is_verified', 'created_at', 'last_login']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone_number', 'password', 'id']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number', ''),
            password=validated_data['password'],
        )
        return user
