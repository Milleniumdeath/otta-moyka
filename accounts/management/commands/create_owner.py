from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Email va parol bilan moyka egasi yaratish'

    def handle(self, *args, **kwargs):
        self.stdout.write('=== OTTA — Moyka Egasi Yaratish ===\n')

        email = input('Email: ').strip()
        if not email:
            self.stderr.write('Email bo\'sh bo\'lishi mumkin emas!')
            return

        if User.objects.filter(email=email).exists():
            self.stderr.write(f'{email} allaqachon mavjud!')
            return

        import getpass
        password = getpass.getpass('Parol: ')
        confirm  = getpass.getpass('Parolni tasdiqlang: ')

        if password != confirm:
            self.stderr.write('Parollar mos kelmadi!')
            return

        first_name = input('Ism (ixtiyoriy): ').strip()
        last_name  = input('Familiya (ixtiyoriy): ').strip()

        user = User.objects.create_superuser(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='owner',
            is_approved=True,
            email_verified=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Moyka egasi yaratildi: {user.email}')
        )
