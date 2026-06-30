from django.contrib import admin
from .models import MarketAsset, CryptoPriceHistory, CryptoDepositAddress, OhlcSnapshot


@admin.register(MarketAsset)
class MarketAssetAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'type', 'current_price', 'price_change_24h', 'is_active', 'updated_at']
    list_editable = ['current_price', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(CryptoPriceHistory)
class CryptoPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['asset', 'price_usd', 'timestamp']
    list_filter = ['asset', 'timestamp']


@admin.register(CryptoDepositAddress)
class CryptoDepositAddressAdmin(admin.ModelAdmin):
    list_display = ['asset', 'address', 'is_active', 'updated_at']
    list_editable = ['address', 'is_active']


@admin.register(OhlcSnapshot)
class OhlcSnapshotAdmin(admin.ModelAdmin):
    list_display = ['asset', 'timestamp', 'open', 'high', 'low', 'close']
    list_filter = ['asset', 'timestamp']
