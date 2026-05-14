from django.db import models
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