from django.urls import path
from . import views
from .notification_views import get_notifications, mark_read

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    # Bildirishnomalar API
    path('api/notifications/', get_notifications, name='notifications'),
    path('api/notifications/read/', mark_read, name='notifications_read'),
]
