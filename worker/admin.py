from django.contrib import admin
from .models import ServiceAd
from .models import WorkSchedule

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display  = ['worker', 'get_weekday_display', 'start_time', 'end_time', 'is_active']
    list_filter   = ['weekday', 'is_active']
    search_fields = ['worker__email']

@admin.register(ServiceAd)
class ServiceAdAdmin(admin.ModelAdmin):
    list_display = ('worker', 'title', 'service_type', 'price', 'is_active', 'created_at')
    list_filter = ('service_type', 'is_active')
    search_fields = ('worker__email', 'title')
