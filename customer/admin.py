from django.contrib import admin
from .models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('owner', 'brand', 'model', 'plate_number', 'car_type', 'created_at')
    list_filter = ('car_type',)
    search_fields = ('owner__email', 'plate_number', 'brand')
