from decimal import Decimal
from django.db import models


class MarketAsset(models.Model):
    class AssetType(models.TextChoices):
        CRYPTO = 'CRYPTO', 'Cryptocurrency'

    type = models.CharField(max_length=10, choices=AssetType.choices, default=AssetType.CRYPTO)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    coingecko_id = models.CharField(max_length=100, blank=True, null=True)
    symbol = models.CharField(max_length=10, blank=True)
    current_price = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'))
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    price_high_24h = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'))
    price_low_24h = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'))
    market_cap = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=24, decimal_places=2, default=Decimal('0'))
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.code} — ${self.current_price}"


class CryptoPriceHistory(models.Model):
    asset = models.ForeignKey(MarketAsset, on_delete=models.CASCADE, related_name='price_history')
    price_usd = models.DecimalField(max_digits=18, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.asset.code} @ {self.timestamp}"


class CryptoDepositAddress(models.Model):
    asset = models.OneToOneField(MarketAsset, on_delete=models.CASCADE, related_name='deposit_address')
    address = models.CharField(max_length=255)
    label = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deposit Address'
        verbose_name_plural = 'Deposit Addresses'

    def __str__(self):
        return f"{self.asset.code}: {self.address[:20]}..."


class OhlcSnapshot(models.Model):
    asset = models.ForeignKey(MarketAsset, on_delete=models.CASCADE, related_name='ohlc_snapshots')
    timestamp = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=18, decimal_places=8)
    high = models.DecimalField(max_digits=18, decimal_places=8)
    low = models.DecimalField(max_digits=18, decimal_places=8)
    close = models.DecimalField(max_digits=18, decimal_places=8)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['asset', 'timestamp'])]

    def __str__(self):
        return f"{self.asset.code} OHLC @ {self.timestamp}"
