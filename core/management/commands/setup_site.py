"""Initial PythonAnywhere/production setup: Site domeni + Google SocialApp.

Ishlatish (PythonAnywhere Bash konsolida):
    python manage.py setup_site

Site domain: SITE_DOMAIN env > ALLOWED_HOSTS dagi birinchi qiymat.
Google OAuth uchun GOOGLE_CLIENT_ID va GOOGLE_CLIENT_SECRET kerak.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Site domeni va Google SocialApp'ni env qiymatlaridan sozlaydi."

    def handle(self, *args, **opts):
        from django.contrib.sites.models import Site

        domain = os.environ.get('SITE_DOMAIN', '').strip()
        if not domain:
            hosts = [h.strip() for h in settings.ALLOWED_HOSTS if h.strip() and h != '*']
            domain = hosts[0] if hosts else 'localhost'

        site, _ = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': 'OTTA Moyka'},
        )
        self.stdout.write(self.style.SUCCESS(f"Site #{site.id} -> {site.domain}"))

        client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
        if not (client_id and client_secret):
            self.stdout.write(self.style.WARNING(
                "GOOGLE_CLIENT_ID/SECRET berilmagan — SocialApp o'tkazib yuborildi."
            ))
            return

        from allauth.socialaccount.models import SocialApp
        app, _ = SocialApp.objects.get_or_create(provider='google', name='Google')
        app.client_id = client_id
        app.secret = client_secret
        app.save()
        app.sites.add(site)
        self.stdout.write(self.style.SUCCESS("Google SocialApp sozlandi."))
