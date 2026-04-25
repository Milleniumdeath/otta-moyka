from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class OttaSocialAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.role:
            user.role = 'customer'
            user.email_verified = True
            user.save()
        return user