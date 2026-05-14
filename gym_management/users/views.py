import uuid

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.conf import settings

from .models import User, UserSession
from .serializers import Users_serializer, RegisterSerializer
from .permissions import AdminOnly, IsSelfOrAdmin
from .services import (
    blacklist_refresh_jti,
    is_refresh_jti_blacklisted,
    create_user_session,
    revoke_session,
    log_audit_event,
)


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class Registeration_view(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(Users_serializer(user).data,
                        status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Login — creates UserSession + AuditLog, sets cookies
# ---------------------------------------------------------------------------

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
            # Audit: failed login (unknown email)
            log_audit_event('LOGIN_FAILED', request, user=None, metadata={"email": email})
            raise AuthenticationFailed("User not found.")

        if not user.check_password(password):
            # Audit: failed login (bad password)
            log_audit_event('LOGIN_FAILED', request, user=user, metadata={"reason": "bad_password"})
            raise AuthenticationFailed("Incorrect password.")

        # Generate a token family for this session
        token_family = uuid.uuid4()

        # Issue JWT pair — embed token_family in the refresh token
        refresh = RefreshToken.for_user(user)
        refresh["token_family"] = str(token_family)

        # Create a tracked session
        session = create_user_session(user, request, token_family=token_family)

        # Audit: successful login
        log_audit_event('LOGIN', request, user=user, metadata={
            "session_id": str(session.id),
        })

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


# ---------------------------------------------------------------------------
# Token Refresh — rotate via Redis blacklist
# ---------------------------------------------------------------------------

class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not raw_refresh:
            raise AuthenticationFailed("Refresh token not found in cookies.")

        try:
            old_refresh = RefreshToken(raw_refresh)
        except TokenError:
            raise AuthenticationFailed("Invalid or expired refresh token.")

        old_jti = old_refresh["jti"]

        # Check if this token was already used (replay attack detection)
        if is_refresh_jti_blacklisted(old_jti):
            # Possible token theft — revoke the entire family
            family_str = old_refresh.get("token_family")
            if family_str:
                UserSession.objects.filter(
                    token_family=family_str, is_active=True
                ).update(is_active=False)
            log_audit_event('TOKEN_REVOKED', request, metadata={
                "reason": "replay_detected", "jti": old_jti,
            })
            raise AuthenticationFailed("Token reuse detected. Session revoked.")

        # Blacklist old JTI in Redis
        blacklist_refresh_jti(old_jti)

        # Issue new pair preserving the token family
        user_id = old_refresh["user_id"]
        user = User.objects.get(id=user_id)
        new_refresh = RefreshToken.for_user(user)
        token_family = old_refresh.get("token_family")
        if token_family:
            new_refresh["token_family"] = token_family
            # Update session last_activity
            UserSession.objects.filter(
                token_family=token_family, is_active=True
            ).update(last_activity=timezone.now())

        response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, new_refresh.access_token, new_refresh)
        return response


# ---------------------------------------------------------------------------
# Logout — revoke session, blacklist refresh token in Redis, clear cookies
# ---------------------------------------------------------------------------

class Logout_view(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                jti = token["jti"]
                # Blacklist in Redis
                blacklist_refresh_jti(jti)

                # Revoke the associated session
                family_str = token.get("token_family")
                if family_str:
                    sessions = UserSession.objects.filter(
                        token_family=family_str, is_active=True
                    )
                    for sess in sessions:
                        revoke_session(sess)
            except TokenError:
                pass  # expired/invalid — still clear cookies

        # Audit: logout
        log_audit_event('LOGOUT', request, user=request.user)

        response = Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)
        _clear_auth_cookies(response)
        return response


# ---------------------------------------------------------------------------
# User management views
# ---------------------------------------------------------------------------

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

