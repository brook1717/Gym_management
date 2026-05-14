from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.conf import settings
from .models import User
from .serializers import Users_serializer, RegisterSerializer
from .permissions import AdminOnly, IsSelfOrAdmin


def _set_auth_cookies(response, access_token, refresh_token):
    """Helper: set access & refresh JWT tokens as HttpOnly, Secure, SameSite=Lax cookies."""
    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE,
        value=str(access_token),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    response.set_cookie(
        key=settings.JWT_AUTH_REFRESH_COOKIE,
        value=str(refresh_token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    return response


def _clear_auth_cookies(response):
    """Helper: delete both JWT cookies."""
    response.delete_cookie(settings.JWT_AUTH_COOKIE, path="/")
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path="/")
    return response


#User Registration
class Registeration_view(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(Users_serializer(user).data,
                        status=status.HTTP_201_CREATED)


#User Login — JWT tokens set exclusively in HttpOnly cookies
class Login_view(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        #validation before any database queries
        if not password:
            raise ValidationError("Password is required.")
        if not email:
            raise ValidationError("Email is required.")

        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            raise AuthenticationFailed("User not found.")

        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect password.")

        #JWT Token generation — stored in cookies only
        refresh = RefreshToken.for_user(user)

        response = Response({
            "detail": "Login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            }
        }, status=status.HTTP_200_OK)

        _set_auth_cookies(response, refresh.access_token, refresh)
        return response


#Token Refresh — reads refresh token from cookie, returns new pair in cookies
class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not raw_refresh:
            raise AuthenticationFailed("Refresh token not found in cookies.")
        try:
            old_refresh = RefreshToken(raw_refresh)
            # Rotate: blacklist old, issue new pair
            old_refresh.blacklist()
            user_id = old_refresh["user_id"]
            user = User.objects.get(id=user_id)
            new_refresh = RefreshToken.for_user(user)
        except TokenError:
            raise AuthenticationFailed("Invalid or expired refresh token.")

        response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, new_refresh.access_token, new_refresh)
        return response


#Logout — blacklist refresh token and clear cookies
class Logout_view(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # already blacklisted or expired — still clear cookies

        response = Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)
        _clear_auth_cookies(response)
        return response



#admin only list all users
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [AdminOnly]

#User detail (for only self or admin)
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = Users_serializer
    permission_classes = [IsSelfOrAdmin]

#Authenticated user profile only self
class UserProfileView(generics.RetrieveAPIView):
    serializer_class = Users_serializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

