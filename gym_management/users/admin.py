from django.contrib import admin
from .models import User, MemberProfile
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
