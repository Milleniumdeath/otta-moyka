from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver


@receiver(pre_social_login)
def set_default_role(sender, request, sociallogin, **kwargs):
    """Google orqali kirgan yangi foydalanuvchiga customer roli beriladi"""
    if sociallogin.is_existing:
        return  # Allaqachon ro'yxatdan o'tgan

    user = sociallogin.user

    # Superuser rolini o'zgartirma
    if user.is_superuser:
        return

    # Yangi foydalanuvchi — default customer
    user.role = 'customer'