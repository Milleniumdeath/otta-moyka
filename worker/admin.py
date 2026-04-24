from django.contrib import admin
from .models import ServiceAd


@admin.register(ServiceAd)
class ServiceAdAdmin(admin.ModelAdmin):
    list_display = ('worker', 'title', 'service_type', 'price', 'is_active', 'created_at')
    list_filter = ('service_type', 'is_active')
    search_fields = ('worker__email', 'title')
