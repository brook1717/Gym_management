import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


#Custom User Manager (handles user + superuser creation logic)
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        #Ensure required flags for superuser
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


#Custom User model (replaces default Django user)
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('trainer', 'Trainer'),
        ('receptionist', 'Receptionist'),
        ('member', 'Member'),
    ]

    # Primary login identifier
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='member')
    is_verified = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    oauth_provider = models.CharField(max_length=50, blank=True, default='')
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # last_login is provided by AbstractBaseUser

    # Optional contact info (kept for backward compat)
    phone_number = models.CharField(max_length=15, blank=True, default='')

    #User status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.full_name


#Extra profile data for members
class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member_profile")
    gender = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    def __str__(self):
        return f"Here is the Profile of {self.user.full_name}"


# ---------------------------------------------------------------------------
# Session Tracking
# ---------------------------------------------------------------------------

class UserSession(models.Model):
    """Tracks active user sessions with device/browser/IP metadata."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    # Refresh token family — ties a chain of rotated tokens to this session
    token_family = models.UUIDField(default=uuid.uuid4, unique=True)
    device = models.CharField(max_length=255, blank=True, default='')
    browser = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token_family']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.device or 'Unknown'} ({self.ip_address})"


# ---------------------------------------------------------------------------
# Security Audit Log
# ---------------------------------------------------------------------------

class AuditLog(models.Model):
    """Immutable security event log."""
    EVENT_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('MFA_ENABLED', 'MFA Enabled'),
        ('MFA_DISABLED', 'MFA Disabled'),
        ('MFA_CHALLENGE', 'MFA Challenge'),
        ('TOKEN_REVOKED', 'Token Revoked'),
        ('SESSION_REVOKED', 'Session Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs"
    )
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.event} — {self.user_id} @ {self.created_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# MFA Device (TOTP)
# ---------------------------------------------------------------------------

class MFADevice(models.Model):
    """Stores a TOTP authenticator device for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_device"
    )
    # TOTP secret encrypted with Fernet at rest
    encrypted_secret = models.TextField()
    # Hashed single-use backup codes stored as JSON list
    backup_codes = models.JSONField(default=list, blank=True)
    # True once the user has confirmed setup with a valid TOTP code
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MFA Device"
        verbose_name_plural = "MFA Devices"

    def __str__(self):
        status = "confirmed" if self.is_confirmed else "pending"
        return f"TOTP ({status}) — {self.user.email}"