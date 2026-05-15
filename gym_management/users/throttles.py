"""
Custom DRF throttle classes for brute-force protection.
Uses the default cache backend (Redis in production).
"""
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5 attempts per minute per IP on the login endpoint."""
    scope = "login"


class PasswordResetRateThrottle(AnonRateThrottle):
    """3 attempts per minute per IP on the password reset endpoint."""
    scope = "password_reset"


class TokenRefreshRateThrottle(AnonRateThrottle):
    """10 attempts per minute per IP on the token refresh endpoint."""
    scope = "token_refresh"


class MFAVerifyRateThrottle(AnonRateThrottle):
    """5 attempts per minute per IP on the MFA verify endpoint."""
    scope = "mfa_verify"
