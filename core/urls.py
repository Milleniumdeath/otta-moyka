from django.urls import path
from . import views
from .notification_views import get_notifications, mark_read
from .ai_views import ai_chat, lab_generate
from .live_views import live_digest

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    # Bildirishnomalar API
    path('api/notifications/', get_notifications, name='notifications'),
    path('api/notifications/read/', mark_read, name='notifications_read'),
    # AI yordamchi
    path('api/ai-chat/', ai_chat, name='ai_chat'),
    # Lab — kimyoviy formula generatsiyasi
    path('api/lab-generate/', lab_generate, name='lab_generate'),
    # Polling — sahifa avtomatik yangilanishi uchun yengil signatura
    path('api/live-digest/', live_digest, name='live_digest'),
]
