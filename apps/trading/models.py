from decimal import Decimal
from django.db import models
from apps.accounts.models import UserAccount
from apps.market.models import MarketAsset


class Order(models.Model):
    SIDES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    TYPES = [('MARKET', 'Market'), ('LIMIT', 'Limit')]
    STATUSES = [
        ('PENDING', 'Pending'), ('PARTIAL', 'Partially Filled'),
        ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'),
    ]

    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='orders')
    asset = models.ForeignKey(MarketAsset, on_delete=models.PROTECT)
    side = models.CharField(max_length=4, choices=SIDES)
    order_type = models.CharField(max_length=10, choices=TYPES, default='MARKET')
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    filled_quantity = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'))
    limit_price = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    price_at_exec = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    total_fiat = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    fee_currency = models.CharField(max_length=3, default='USD')
    pnl = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.side} {self.quantity} {self.asset.code} @ ${self.price_at_exec}"
