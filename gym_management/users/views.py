from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import User
from rest_framework.exceptions import AuthenticationFailed
from .permissions import AdminOnly
import jwt, datetime
from .serializers import Users_serializer, RegisterSerializer, LogoutSerializer
from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed

class Registeration_view(APIView):
    authentication_classes = [] 
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(Users_serializer(user).data)
    
class Login_view(APIView):
    authentication_classes = [] 
    permission_classes = [AllowAny]
    def post(self, request):
        phone_number = request.data['phone_number']
        email = request.data['email']
        password = request.data['password']

        user = User.objects.filter(phone_number=phone_number).first()

        if user is None:
            raise AuthenticationFailed("User not Found")
        
        if not user.check_password(password):
            raise AuthenticationFailed('incorrect Password')
        
        

        
        # payload = {
        #      'id': user.id,
        #      'exp': datetime.datetime.utcnow() +datetime.timedelta(minutes=60),
        #      'iat': datetime.datetime.utcnow()
        #  }
        
        # token = jwt.encode(payload, 'secret', algorithm='HS256')

        # response = Response()
        # response.set_cookie(key='jwt', value=token, httponly='True')
        
        # response.data = {
        #     'jwt': token
        # }


        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        return Response({
            "access": access,
            "refresh": str(refresh)
            })




        # return response
#authenticated user

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [AdminOnly]



#log out blacklisting from django simple jwt

class Logout_view(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    permission_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"Message":"User logged out"})