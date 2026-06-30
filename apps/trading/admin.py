from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['account', 'side', 'order_type', 'asset', 'quantity', 'filled_quantity', 'price_at_exec', 'status', 'pnl', 'created_at']
    list_filter = ['side', 'order_type', 'status', 'created_at']
    search_fields = ['account__user__username', 'asset__code']
    readonly_fields = ['account', 'asset', 'side', 'order_type', 'quantity', 'filled_quantity', 'limit_price', 'price_at_exec', 'total_fiat', 'fee', 'pnl', 'created_at', 'updated_at']
