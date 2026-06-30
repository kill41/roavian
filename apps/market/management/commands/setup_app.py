from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from apps.market.models import MarketAsset


class Command(BaseCommand):
    help = 'One-time setup: seed assets + prices + admin user'

    def handle(self, *args, **options):
        if not MarketAsset.objects.exists():
            call_command('seed_cryptos')
            call_command('fetch_prices')
            self.stdout.write('Seeded MarketAssets and initial prices')
        else:
            call_command('fetch_prices')
            self.stdout.write('Prices refreshed')

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            admin = User.objects.get(username='admin')
            admin.first_name = 'Admin'
            admin.last_name = 'User'
            admin.save()
            admin.account.cash_balance = Decimal('100000.00')
            admin.account.save()
            for code, bal in [('BTC', 2), ('ETH', 10), ('SOL', 10)]:
                asset = MarketAsset.objects.filter(code=code).first()
                if asset:
                    from apps.accounts.models import UserHolding
                    UserHolding.objects.create(
                        account=admin.account, asset=asset,
                        balance=Decimal(str(bal)),
                        average_entry_price=asset.current_price,
                    )
            self.stdout.write('Created superuser: admin / admin123 (funded with $100,000 + BTC/ETH/SOL)')
        else:
            admin = User.objects.filter(is_superuser=True).first()
            if admin and admin.account.cash_balance < Decimal('1000'):
                admin.account.cash_balance = Decimal('100000.00')
                admin.account.save()
                self.stdout.write('Admin account re-funded')
