from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .permissions import AdminOnly
import jwt, datetime
from .serializers import Users_serializer, RegisterSerializer, LogoutSerializer
from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from .permissions import AdminOnly, StaffOrAdmin, IsSelfOrAdmin

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

        #validation
        if not password:
            raise ValidationError("Password is required")
        
        if not phone_number and not email:
            raise ValidationError("Phone number or email is required")
        if phone_number:
            user = User.objects.filter(phone_number=phone_number).first()
        else:
            user = User.objects.filter(email=email).first()
        

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
            "refresh": str(refresh),
            "user": { 
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "role": user.role
            }
            })



#log out blacklisting from django simple jwt

class Logout_view(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    permission_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"Message":"User logged out"})
    


    
#admin permision

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [AdminOnly]

#admin or member/self
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [IsSelfOrAdmin]

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = Users_serializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

