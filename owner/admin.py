from django.contrib import admin
from .models import PriceList

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['service_type', 'min_price', 'max_price', 'recommended_price', 'is_active']
    list_filter  = ['is_active', 'service_type']

