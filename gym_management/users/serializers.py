from rest_framework import serializers
from users.models import User
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

class Users_serializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'full_name', 'email', 'role']
        read_only_feilds = ['id','role']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'email', 'password', 'id']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            full_name=validated_data['full_name'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user
    


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


    def validate(self, attrs):
        self.token = attrs['refresh']


        return attrs
    
    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad token')
