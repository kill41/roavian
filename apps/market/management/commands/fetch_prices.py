from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import close_old_connections
from apps.market.models import MarketAsset, CryptoPriceHistory
from apps.market.coingecko import CoinGeckoClient
import time

COIN_IDS = [
    'bitcoin', 'ethereum', 'solana', 'ripple', 'cardano', 'avalanche-2',
    'polkadot', 'chainlink', 'dogecoin', 'matic-network', 'internet-computer',
    'shiba-inu', 'cosmos', 'aptos', 'injective-protocol', 'thorchain',
    'optimism', 'arbitrum', 'celestia', 'sui', 'fetch-ai', 'beam',
    'tether', 'usd-coin', 'stellar', 'near', 'kaspa', 'hedera-hashgraph',
]


def safe_decimal(val, default='0'):
    if val is None:
        return None if default is None else Decimal(default)
    try:
        if isinstance(val, float):
            val = round(val, 8)
        return Decimal(str(val))
    except Exception:
        return None if default is None else Decimal(default)


class Command(BaseCommand):
    help = 'Fetch prices from CoinGecko coins/markets endpoint'

    def handle(self, *args, **options):
        close_old_connections()
        client = CoinGeckoClient()
        batch_size = 25
        total = 0

        for i in range(0, len(COIN_IDS), batch_size):
            batch = COIN_IDS[i:i + batch_size]
            try:
                data = client.get_coin_markets(batch)
            except Exception as e:
                self.stderr.write(f'Error fetching batch {i}: {e}')
                continue

            if not data or not isinstance(data, list):
                self.stderr.write(f'Empty response for batch {i}')
                continue

            for item in data:
                cid = item.get('id', '')
                if not cid:
                    continue
                try:
                    asset, _ = MarketAsset.objects.update_or_create(
                        coingecko_id=cid,
                        defaults={
                            'code': item.get('symbol', cid).upper(),
                            'name': item.get('name', cid),
                            'current_price': safe_decimal(item.get('current_price'), '0'),
                            'price_change_24h': safe_decimal(item.get('price_change_percentage_24h'), '0'),
                            'price_high_24h': safe_decimal(item.get('high_24h'), '0'),
                            'price_low_24h': safe_decimal(item.get('low_24h'), '0'),
                            'market_cap': safe_decimal(item.get('market_cap'), None),
                            'volume_24h': safe_decimal(item.get('total_volume'), '0'),
                            'image_url': item.get('image', ''),
                            'is_active': True,
                            'sort_order': item.get('market_cap_rank', 999) or 999,
                            'type': MarketAsset.AssetType.CRYPTO,
                        }
                    )
                    CryptoPriceHistory.objects.create(asset=asset, price_usd=asset.current_price)
                    total += 1
                except Exception as e:
                    self.stderr.write(f'Error saving {cid}: {e}')

            if i + batch_size < len(COIN_IDS):
                time.sleep(2)

        self.stdout.write(f'Updated {total} assets at {now()}')
