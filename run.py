import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from decimal import Decimal
from apps.market.scheduler import PriceScheduler
from apps.market.models import MarketAsset
import time


def setup():
    PriceScheduler.stop()
    time.sleep(1)

    if not MarketAsset.objects.exists():
        call_command('seed_cryptos')
        call_command('fetch_prices')
    else:
        call_command('fetch_prices')

    if not User.objects.filter(is_superuser=True).exists():
        u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        u.first_name = 'Admin'
        u.last_name = 'User'
        u.save()
        u.account.cash_balance = Decimal('100000.00')
        u.account.save()
        for code in ['BTC', 'ETH', 'SOL']:
            asset = MarketAsset.objects.filter(code=code).first()
            if asset:
                from apps.accounts.models import UserHolding
                UserHolding.objects.create(account=u.account, asset=asset,
                    balance=Decimal('2.0') if code == 'BTC' else Decimal('10.0'),
                    average_entry_price=asset.current_price)
        print('Created superuser: admin / admin123 (funded with $100,000 USD + crypto)')
    else:
        admin = User.objects.filter(is_superuser=True).first()
        if admin and admin.account.cash_balance < Decimal('1000'):
            admin.account.cash_balance = Decimal('100000.00')
            admin.account.save()
            print('Admin account re-funded with demo balance')


if __name__ == '__main__':
    setup()
    PriceScheduler.start(interval=60)
    print('Starting Roavian server at http://127.0.0.1:8000')
    call_command('runserver', '127.0.0.1:8000', '--noreload')
