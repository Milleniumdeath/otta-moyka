from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import pwa

urlpatterns = [
    # Admin panel (faqat superuser uchun)
    path('admin/', admin.site.urls),

    # PWA (root scope shart — service worker butun saytni boshqaradi)
    path('manifest.webmanifest', pwa.manifest, name='pwa_manifest'),
    path('sw.js', pwa.service_worker, name='pwa_sw'),
    path('offline/', pwa.offline, name='pwa_offline'),

    # Landing page
    path('', include('core.urls')),

    # Autentifikatsiya (login, register, Google OAuth)
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),

    # Rol sahifalari
    path('owner/', include('owner.urls')),
    path('worker/', include('worker.urls')),
    path('customer/', include('customer.urls')),
]

# Development da media fayllarni serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
