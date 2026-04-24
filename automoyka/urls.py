from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin panel (faqat superuser uchun)
    path('admin/', admin.site.urls),

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
