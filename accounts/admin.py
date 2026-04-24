from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User, EmailVerificationCode


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['email', 'get_full_name', 'role', 'is_approved', 'email_verified', 'is_active']
    list_filter   = ['role', 'is_approved', 'email_verified', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering      = ['-date_joined']

    fieldsets = UserAdmin.fieldsets + (
        ('OTTA Ma\'lumotlar', {
            'fields': ('role', 'phone', 'avatar', 'is_approved', 'email_verified')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('OTTA Ma\'lumotlar', {
            'fields': ('role', 'phone', 'is_approved')
        }),
    )


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at']
    list_filter  = ['created_at']
