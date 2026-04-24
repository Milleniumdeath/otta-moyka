from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER    = 'owner',    'Moyka Egasi'
        WORKER   = 'worker',   'Ishchi'
        CUSTOMER = 'customer', 'Mijoz'

    role           = models.CharField(max_length=20, choices=Role.choices, default='customer')
    phone          = models.CharField(max_length=20, blank=True, null=True)
    avatar         = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_approved    = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER or self.is_superuser

    @property
    def is_worker(self):
        return self.role == self.Role.WORKER

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    def __str__(self):
        return self.email or self.username


class EmailVerificationCode(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code       = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    class Meta:
        ordering = ['-created_at']
