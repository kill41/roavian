from django.core.management.base import BaseCommand
from apps.market.models import MarketAsset, CryptoDepositAddress


COINS = [
    ('BTC', 'Bitcoin', 'bitcoin', '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', 1),
    ('ETH', 'Ethereum', 'ethereum', '0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18', 2),
    ('SOL', 'Solana', 'solana', '7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV', 3),
    ('XRP', 'XRP', 'ripple', 'rLHzPsX1B1dEJqBnbBB1J1dQxPkCE6mPpG', 4),
    ('ADA', 'Cardano', 'cardano', 'DdzFFzCqrhshMSx7sV7Kj9xL4wL9rCsyL4fJWdT3tFqSA', 5),
    ('AVAX', 'Avalanche', 'avalanche-2', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 6),
    ('DOT', 'Polkadot', 'polkadot', '14Zx3Xy5Z7a9B1c3D5e7F9gH1iJ3kL5mN7oP9qR', 7),
    ('LINK', 'Chainlink', 'chainlink', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 8),
    ('DOGE', 'Dogecoin', 'dogecoin', 'D5ZnGirVnBS6j7cX5Yhi3MGEzABCSXJZRq', 9),
    ('MATIC', 'Polygon', 'matic-network', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 10),
    ('UNI', 'Uniswap', 'uniswap', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 11),
    ('SHIB', 'Shiba Inu', 'shiba-inu', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 12),
    ('ATOM', 'Cosmos', 'cosmos', 'cosmos1q4k3d0f5j6h7g8f9d0s1a2z3x4c5v6b7n8m9q', 13),
    ('APT', 'Aptos', 'aptos', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 14),
    ('INJ', 'Injective', 'injective-protocol', 'inj1q4k3d0f5j6h7g8f9d0s1a2z3x4c5v6b7n8m9q', 15),
    ('RUNE', 'THORChain', 'thorchain', 'thor1q4k3d0f5j6h7g8f9d0s1a2z3x4c5v6b7n8m9q', 16),
    ('OP', 'Optimism', 'optimism', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 17),
    ('ARB', 'Arbitrum', 'arbitrum', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 18),
    ('TIA', 'Celestia', 'celestia', 'celestia1q4k3d0f5j6h7g8f9d0s1a2z3x4c5v6b7n8m9q', 19),
    ('SUI', 'Sui', 'sui', '0x5c5e3D8C9Fc3F1a3b4c5D6e7F8g9H0iJ1kL2mN', 20),
    ('FET', 'Fetch.ai', 'fetch-ai', 'fetch1q4k3d0f5j6h7g8f9d0s1a2z3x4c5v6b7n8m9q', 21),
]


class Command(BaseCommand):
    help = 'Seed initial MarketAssets and deposit addresses'

    def handle(self, *args, **options):
        for code, name, cid, addr, order in COINS:
            asset, _ = MarketAsset.objects.update_or_create(
                coingecko_id=cid,
                defaults={
                    'type': MarketAsset.AssetType.CRYPTO,
                    'code': code,
                    'name': name,
                    'sort_order': order,
                    'is_active': True,
                }
            )
            CryptoDepositAddress.objects.update_or_create(
                asset=asset,
                defaults={'address': addr, 'is_active': True},
            )
        self.stdout.write(f'Seeded {len(COINS)} MarketAssets with deposit addresses')
