from django.contrib import admin
from .models import Expense, Income

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'group', 'amount', 'date')
    list_filter = ('group', 'date')

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'order', 'date')
    list_filter = ('category', 'date')