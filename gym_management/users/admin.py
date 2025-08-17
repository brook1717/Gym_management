from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin
from django.forms import TextInput, Textarea


#simplified the Admin site
class Admin_site_Configurations(UserAdmin):
    ordering=('-full_name',)
    list_display = ('phone_number', 'full_name', 'email', 'role', 'is_active', 'is_staff')
    search_fields = ['phone_number', 'full_name', 'email']


    fieldsets =(
        (None, {'fields':('phone_number', 'full_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser') }),
        

    )

    add_fieldsets=(
        (
            None,{
                'classes':('wide',),
                'fields': ('phone_number', 'full_name', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
            },
        ),
    )

admin.site.register(User, Admin_site_Configurations)
