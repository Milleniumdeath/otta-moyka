from django.contrib import admin
from .models import Order, Review, LoyaltyToken, LoyaltyTransaction, Bonus, BonusClaim


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'worker', 'car', 'status', 'total_price', 'created_at')
    list_filter = ('status',)
    search_fields = ('customer__email', 'worker__email')
    ordering = ('-created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(LoyaltyToken)
class LoyaltyTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_earned', 'total_spent', 'updated_at')
    search_fields = ('user__email',)


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('loyalty', 'tx_type', 'amount', 'description', 'created_at')
    list_filter = ('tx_type',)


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ('name', 'token_cost', 'quantity', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(BonusClaim)
class BonusClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'bonus', 'created_at')
