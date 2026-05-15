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

from .models import User, UserSession, MemberProfile, MFADevice
from .serializers import (
    Users_serializer, RegisterSerializer, MemberProfileSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    OAuthCallbackSerializer, MFASetupConfirmSerializer, MFAVerifySerializer,
)
from .permissions import AdminOnly, IsAdmin, IsTrainer, IsOwnerOrReadOnly, IsSelfOrAdmin
from .services import (
    blacklist_refresh_jti,
    is_refresh_jti_blacklisted,
    create_user_session,
    revoke_session,
    revoke_all_sessions,
    log_audit_event,
    send_verification_email,
    verify_email_token,
    send_password_reset_email,
    verify_password_reset_token,
    exchange_oauth_code,
    generate_mfa_token,
    verify_mfa_token,
    generate_totp_secret,
    encrypt_totp_secret,
    decrypt_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_code,
    generate_backup_codes,
    verify_backup_code,
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
        # Send verification email on registration
        send_verification_email(user)
        return Response(
            {
                "detail": "Registration successful. Please check your email to verify your account.",
                "user": Users_serializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Shared helper — complete login (issue JWT cookies + session + audit)
# ---------------------------------------------------------------------------

def _complete_login(user, request):
    """
    Issue JWT cookies, create a UserSession, write LOGIN audit.
    Returns a fully formed Response.
    """
    token_family = uuid.uuid4()
    refresh = RefreshToken.for_user(user)
    refresh["token_family"] = str(token_family)

    session = create_user_session(user, request, token_family=token_family)
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
# Login — MFA-aware: returns mfa_token if MFA enabled, else full login
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

        # If MFA is enabled AND a confirmed device exists → defer to MFA challenge
        if user.mfa_enabled and MFADevice.objects.filter(user=user, is_confirmed=True).exists():
            mfa_token = generate_mfa_token(user)
            log_audit_event('MFA_CHALLENGE', request, user=user)
            return Response({
                "detail": "MFA required.",
                "mfa_required": True,
                "mfa_token": mfa_token,
            }, status=status.HTTP_200_OK)

        return _complete_login(user, request)


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
# Email Verification
# ---------------------------------------------------------------------------

class SendVerificationEmailView(APIView):
    """Re-send a verification email to the authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_verified:
            return Response({"detail": "Email already verified."}, status=status.HTTP_200_OK)
        send_verification_email(user)
        return Response(
            {"detail": "Verification email sent."},
            status=status.HTTP_200_OK,
        )


class VerifyEmailView(APIView):
    """Verify an email address using a signed token."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            raise ValidationError("Token is required.")

        payload = verify_email_token(token)
        if payload is None:
            return Response(
                {"detail": "Invalid or expired verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=payload["uid"])
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_verified:
            return Response({"detail": "Email already verified."}, status=status.HTTP_200_OK)

        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class PasswordResetView(APIView):
    """Request a password-reset email. Always returns 200 to avoid email enumeration."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user:
            send_password_reset_email(user)

        # Always return 200 to prevent email enumeration
        return Response(
            {"detail": "If an account with that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Validate the reset token and set a new password."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        payload = verify_password_reset_token(token)
        if payload is None:
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=payload["uid"])
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Single-use check: password hash fragment must still match
        if user.password[-8:] != payload.get("ph"):
            return Response(
                {"detail": "This reset link has already been used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Invalidate all existing sessions for this user
        revoke_all_sessions(user)

        # Audit: password reset
        log_audit_event('PASSWORD_RESET', request, user=user)

        return Response(
            {"detail": "Password reset successful. All sessions have been revoked."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# OAuth 2.0 callback
# ---------------------------------------------------------------------------

class OAuthCallbackView(APIView):
    """
    Accept {provider, code} from the frontend, exchange with provider,
    create or update local user, issue JWT cookies.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OAuthCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        code = serializer.validated_data["code"]

        try:
            user_info = exchange_oauth_code(provider, code)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get("email")
        if not email:
            return Response(
                {"detail": "Could not retrieve email from provider."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create or update local user
        user, created = User.objects.get_or_create(
            email__iexact=email,
            defaults={
                "email": email,
                "full_name": user_info.get("full_name", ""),
                "oauth_provider": provider,
                "is_verified": True,
            },
        )
        if not created:
            # Update provider info on returning user
            if not user.oauth_provider:
                user.oauth_provider = provider
            user.is_verified = True
            user.save(update_fields=["oauth_provider", "is_verified"])

        # If user has MFA → require MFA even for OAuth login
        if user.mfa_enabled and MFADevice.objects.filter(user=user, is_confirmed=True).exists():
            mfa_token = generate_mfa_token(user)
            log_audit_event('MFA_CHALLENGE', request, user=user, metadata={"via": "oauth"})
            return Response({
                "detail": "MFA required.",
                "mfa_required": True,
                "mfa_token": mfa_token,
            }, status=status.HTTP_200_OK)

        return _complete_login(user, request)


# ---------------------------------------------------------------------------
# MFA — Setup
# ---------------------------------------------------------------------------

class MFASetupView(APIView):
    """
    POST: Generate a TOTP secret and return the provisioning URI + backup codes.
    The device is NOT confirmed yet — user must verify with a code first.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Delete any unconfirmed device to allow re-setup
        MFADevice.objects.filter(user=user, is_confirmed=False).delete()

        if MFADevice.objects.filter(user=user, is_confirmed=True).exists():
            return Response(
                {"detail": "MFA is already enabled. Disable it first to reconfigure."},
                status=status.HTTP_409_CONFLICT,
            )

        secret = generate_totp_secret()
        plain_codes, hashed_codes = generate_backup_codes()

        MFADevice.objects.create(
            user=user,
            encrypted_secret=encrypt_totp_secret(secret),
            backup_codes=hashed_codes,
            is_confirmed=False,
        )

        return Response({
            "detail": "Scan the QR code with your authenticator app, then confirm with a code.",
            "provisioning_uri": get_totp_provisioning_uri(secret, user.email),
            "secret": secret,          # shown once — for manual entry
            "backup_codes": plain_codes,  # shown once — user must save them
        }, status=status.HTTP_200_OK)


class MFASetupConfirmView(APIView):
    """
    POST {code}: Confirm TOTP setup by verifying the first code.
    Enables MFA on the user account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFASetupConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        device = MFADevice.objects.filter(user=user, is_confirmed=False).first()
        if device is None:
            return Response(
                {"detail": "No pending MFA setup found. Start setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = decrypt_totp_secret(device.encrypted_secret)
        if not verify_totp_code(secret, serializer.validated_data["code"]):
            return Response(
                {"detail": "Invalid code. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.is_confirmed = True
        device.save(update_fields=["is_confirmed"])

        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled"])

        log_audit_event('MFA_ENABLED', request, user=user)
        return Response({"detail": "MFA enabled successfully."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MFA — Verify (login step 2)
# ---------------------------------------------------------------------------

class MFAVerifyView(APIView):
    """
    POST {mfa_token, code}: Validate TOTP (or backup code) after password login.
    Issues JWT cookies on success.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = verify_mfa_token(serializer.validated_data["mfa_token"])
        if payload is None:
            return Response(
                {"detail": "Invalid or expired MFA token. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=payload["uid"])
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        device = MFADevice.objects.filter(user=user, is_confirmed=True).first()
        if device is None:
            return Response({"detail": "No MFA device configured."}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data["code"]
        secret = decrypt_totp_secret(device.encrypted_secret)

        if verify_totp_code(secret, code):
            # TOTP code valid
            return _complete_login(user, request)

        # Try backup code
        idx = verify_backup_code(code, device.backup_codes)
        if idx is not None:
            # Consume the backup code (single-use)
            codes = list(device.backup_codes)
            codes.pop(idx)
            device.backup_codes = codes
            device.save(update_fields=["backup_codes"])
            return _complete_login(user, request)

        log_audit_event('LOGIN_FAILED', request, user=user, metadata={"reason": "bad_mfa_code"})
        return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# MFA — Disable
# ---------------------------------------------------------------------------

class MFADisableView(APIView):
    """DELETE: Disable MFA and remove the device."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        MFADevice.objects.filter(user=user).delete()
        user.mfa_enabled = False
        user.save(update_fields=["mfa_enabled"])
        log_audit_event('MFA_DISABLED', request, user=user)
        return Response({"detail": "MFA disabled."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MFA — Regenerate backup codes
# ---------------------------------------------------------------------------

class MFABackupCodesRegenerateView(APIView):
    """POST: Generate a fresh set of backup codes (requires confirmed MFA device)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device = MFADevice.objects.filter(user=request.user, is_confirmed=True).first()
        if device is None:
            return Response({"detail": "MFA is not enabled."}, status=status.HTTP_400_BAD_REQUEST)

        plain_codes, hashed_codes = generate_backup_codes()
        device.backup_codes = hashed_codes
        device.save(update_fields=["backup_codes"])

        return Response({
            "detail": "New backup codes generated. Save them securely.",
            "backup_codes": plain_codes,
        }, status=status.HTTP_200_OK)


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


# ---------------------------------------------------------------------------
# Demo: Member editing own profile (IsOwnerOrReadOnly)
# ---------------------------------------------------------------------------

class MemberProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  — any authenticated user can read their own profile.
    PUT/PATCH — only the owning member can edit (IsOwnerOrReadOnly).
    """
    serializer_class = MemberProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_object(self):
        profile, _ = MemberProfile.objects.get_or_create(user=self.request.user)
        self.check_object_permissions(self.request, profile)
        return profile


# ---------------------------------------------------------------------------
# Demo: Trainer viewing assigned members (IsTrainer | IsAdmin)
# ---------------------------------------------------------------------------

class TrainerMemberListView(generics.ListAPIView):
    """
    Trainers (and admins) can list member-role users.
    In a full implementation this would filter by trainer assignment;
    here we return all members as a demo of role gating.
    """
    serializer_class = Users_serializer
    permission_classes = [IsTrainer | IsAdmin]

    def get_queryset(self):
        return User.objects.filter(role='member')


# ---------------------------------------------------------------------------
# Demo: Admin-only system settings (IsAdmin)
# ---------------------------------------------------------------------------

class SystemSettingsView(APIView):
    """Dummy admin-only endpoint demonstrating full-access gating."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "maintenance_mode": False,
            "allow_registration": True,
            "default_membership_days": 30,
        })

    def put(self, request):
        # In production this would persist to a SystemConfig model/cache.
        return Response({"detail": "System settings updated."}, status=status.HTTP_200_OK)

