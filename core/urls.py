from django.urls import path
from . import views
from .notification_views import get_notifications, mark_read
from .ai_views import ai_chat

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    # Bildirishnomalar API
    path('api/notifications/', get_notifications, name='notifications'),
    path('api/notifications/read/', mark_read, name='notifications_read'),
    # AI yordamchi
    path('api/ai-chat/', ai_chat, name='ai_chat'),
]
