"""
Service layer for token blacklisting via Redis, session/audit helpers,
and email verification / password reset flows.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

from .models import UserSession, AuditLog


# ---------------------------------------------------------------------------
# Redis-backed Refresh Token Blacklist
# ---------------------------------------------------------------------------

def blacklist_refresh_jti(jti: str, expires_in: timedelta | None = None):
    """
    Mark a refresh token JTI as blacklisted in Redis.
    TTL defaults to the refresh token lifetime so keys auto-expire.
    """
    if expires_in is None:
        expires_in = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    key = f"{settings.REDIS_TOKEN_BLACKLIST_PREFIX}{jti}"
    cache.set(key, "1", timeout=int(expires_in.total_seconds()))


def is_refresh_jti_blacklisted(jti: str) -> bool:
    """Check if a refresh token JTI has been blacklisted."""
    key = f"{settings.REDIS_TOKEN_BLACKLIST_PREFIX}{jti}"
    return cache.get(key) is not None


# ---------------------------------------------------------------------------
# Request metadata helpers
# ---------------------------------------------------------------------------

def get_client_ip(request) -> str:
    """Extract real client IP from request (respects X-Forwarded-For)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def parse_user_agent(ua_string: str) -> dict:
    """Parse User-Agent into device/browser info."""
    try:
        from ua_parser import user_agent_parser
        parsed = user_agent_parser.Parse(ua_string)
        browser = parsed.get("user_agent", {})
        os_info = parsed.get("os", {})
        device = parsed.get("device", {})
        return {
            "browser": f"{browser.get('family', '')} {browser.get('major', '')}".strip(),
            "device": f"{device.get('family', '')}".strip() or f"{os_info.get('family', '')} {os_info.get('major', '')}".strip(),
        }
    except ImportError:
        return {"browser": ua_string[:100], "device": ""}


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_user_session(user, request, token_family: uuid.UUID | None = None) -> UserSession:
    """Create a UserSession record tied to a refresh token family."""
    ua = request.META.get("HTTP_USER_AGENT", "")
    info = parse_user_agent(ua)
    ip = get_client_ip(request)
    if token_family is None:
        token_family = uuid.uuid4()

    session = UserSession.objects.create(
        user=user,
        token_family=token_family,
        device=info["device"],
        browser=info["browser"],
        ip_address=ip or None,
    )
    return session


def revoke_session(session: UserSession):
    """Deactivate a session."""
    session.is_active = False
    session.save(update_fields=["is_active"])


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def log_audit_event(event: str, request, user=None, metadata: dict | None = None):
    """Write an immutable audit log entry."""
    AuditLog.objects.create(
        user=user,
        event=event,
        ip_address=get_client_ip(request) or None,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Signed-token helpers (email verification & password reset)
# ---------------------------------------------------------------------------

def generate_email_verify_token(user) -> str:
    """Create a short-lived signed token for email verification."""
    return signing.dumps(
        {"uid": str(user.pk), "purpose": "email-verify"},
        salt=settings.EMAIL_VERIFY_SALT,
    )


def verify_email_token(token: str) -> dict | None:
    """
    Validate an email-verification token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        return signing.loads(
            token,
            salt=settings.EMAIL_VERIFY_SALT,
            max_age=settings.EMAIL_VERIFY_TOKEN_MAX_AGE,
        )
    except (signing.SignatureExpired, signing.BadSignature):
        return None


def generate_password_reset_token(user) -> str:
    """
    Create a single-use signed token for password reset.
    Embeds the user's current password hash fragment so the token is
    automatically invalidated once the password changes.
    """
    return signing.dumps(
        {
            "uid": str(user.pk),
            "purpose": "password-reset",
            "ph": user.password[-8:],   # last 8 chars of hashed password
        },
        salt=settings.PASSWORD_RESET_SALT,
    )


def verify_password_reset_token(token: str) -> dict | None:
    """
    Validate a password-reset token.
    Returns the payload dict or None if invalid/expired.
    The caller must still verify `payload["ph"]` matches the user's
    current password hash to enforce single-use semantics.
    """
    try:
        return signing.loads(
            token,
            salt=settings.PASSWORD_RESET_SALT,
            max_age=settings.PASSWORD_RESET_TOKEN_MAX_AGE,
        )
    except (signing.SignatureExpired, signing.BadSignature):
        return None


# ---------------------------------------------------------------------------
# Email senders (swap for Celery tasks later)
# ---------------------------------------------------------------------------

def send_verification_email(user):
    """Send an email-verification link to the user."""
    token = generate_email_verify_token(user)
    verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    send_mail(
        subject="Verify your email — Gym Management",
        message=(
            f"Hi {user.full_name},\n\n"
            f"Please verify your email by clicking the link below:\n\n"
            f"{verify_url}\n\n"
            f"This link expires in 24 hours.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset_email(user):
    """Send a password-reset link to the user."""
    token = generate_password_reset_token(user)
    reset_url = f"{settings.FRONTEND_URL}/auth/password-reset-confirm?token={token}"
    send_mail(
        subject="Reset your password — Gym Management",
        message=(
            f"Hi {user.full_name},\n\n"
            f"Click the link below to reset your password:\n\n"
            f"{reset_url}\n\n"
            f"This link expires in 30 minutes and can only be used once.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def revoke_all_sessions(user):
    """Deactivate every active session for a user."""
    UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
