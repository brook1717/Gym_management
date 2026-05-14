"""
Service layer for token blacklisting via Redis and session/audit helpers.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
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
