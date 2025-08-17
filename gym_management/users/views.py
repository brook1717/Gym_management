from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import Users_serializer
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import User
from rest_framework.exceptions import AuthenticationFailed
from .permissions import AdminOnly
import jwt, datetime
from .serializers import Users_serializer
from rest_framework import generics

class Registeration_view(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = Users_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
class Login_view(APIView):
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
        

        
        payload = {
             'id': user.id,
             'exp': datetime.datetime.utcnow() +datetime.timedelta(minutes=60),
             'iat': datetime.datetime.utcnow()
         }
        
        token = jwt.encode(payload, 'secret', algorithm='HS256')

        response = Response()
        response.set_cookie(key='jwt', value=token, httponly='True')
        
        response.data = {
            'jwt': token
        }



        return response
#authenticated user

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [AdminOnly]
