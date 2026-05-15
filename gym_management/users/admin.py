from django.contrib import admin
from .models import User, MemberProfile, UserSession, AuditLog, MFADevice
from django.contrib.auth.admin import UserAdmin


#simplified the Admin site
class Admin_site_Configurations(UserAdmin):
    ordering = ('-full_name',)
    list_display = ('email', 'full_name', 'role', 'is_verified', 'is_active', 'is_staff')
    search_fields = ['email', 'full_name', 'phone_number']
    list_editable = ('role', 'is_active')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff')

    fieldsets = (
        (None, {'fields': ('email', 'full_name', 'phone_number', 'role')}),
        ('Status', {'fields': ('is_verified', 'mfa_enabled', 'oauth_provider', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (
            None, {
                'classes': ('wide',),
                'fields': (
                    'email', 'full_name', 'phone_number', 'role',
                    'password1', 'password2',
                    'is_active', 'is_staff', 'is_superuser',
                ),
            },
        ),
    )


admin.site.register(User, Admin_site_Configurations)
admin.site.register(MemberProfile)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'browser', 'ip_address', 'is_active', 'last_activity')
    list_filter = ('is_active',)
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('id', 'token_family', 'created_at', 'last_activity')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'ip_address', 'created_at')
    list_filter = ('event',)
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('id', 'user', 'event', 'ip_address', 'user_agent', 'metadata', 'created_at')


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_confirmed', 'created_at')
    list_filter = ('is_confirmed',)
    search_fields = ('user__email',)
    readonly_fields = ('id', 'encrypted_secret', 'backup_codes', 'created_at')
