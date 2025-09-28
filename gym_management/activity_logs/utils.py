# activity_logs/utils.py
from .models import ActivityLog
from django.utils import timezone

SENSITIVE_KEYS = {'password', 'token', 'access', 'refresh', 'card_number', 'cvv'}

def _sanitize_metadata(meta):
    if not meta:
        return meta
    try:
        # shallow copy and remove sensitive keys if present
        cleaned = {}
        for k, v in dict(meta).items():
            if k.lower() in SENSITIVE_KEYS:
                cleaned[k] = 'REDACTED'
            else:
                cleaned[k] = v
        return cleaned
    except Exception:
        return None

def log_activity(user=None, action=None, target_type=None, target_id=None, metadata=None, request=None):
    """
    Simple helper to create an ActivityLog entry.
    - user: User instance or None
    - action: short string (e.g. 'MEMBERSHIP_CREATED')
    - target_type: e.g. 'membership', 'payment'
    - target_id: object's id (any -> stored as string)
    - metadata: dict (will be sanitized for sensitive keys)
    - request: optional HttpRequest to capture ip/user-agent
    """
    if not action:
        raise ValueError("action is required for log_activity")

    ip = None
    ua = None
    if request is not None:
        # X-Forwarded-For if behind proxy; fallback to remote addr
        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT')

    ActivityLog.objects.create(
        user=(user if user and getattr(user, 'is_authenticated', True) else None),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        metadata=_sanitize_metadata(metadata),
        ip_address=ip,
        user_agent=ua,
        created_at=timezone.now()
    )
