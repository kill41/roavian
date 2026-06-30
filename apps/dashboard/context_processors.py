def assets_processor(request):
    from django.conf import settings
    from apps.market.models import MarketAsset
    return {
        'assets': MarketAsset.objects.filter(is_active=True),
        'market_indices': [
            {'code': 'GOLD', 'name': 'Gold', 'price': '2345.00', 'change': '+0.3'},
            {'code': 'OIL', 'name': 'Crude Oil', 'price': '78.42', 'change': '-1.2'},
            {'code': 'EUR/USD', 'name': 'Euro', 'price': '1.0824', 'change': '+0.1'},
            {'code': 'S&P 500', 'name': 'S&P 500', 'price': '5432.10', 'change': '+0.8'},
        ],
        'tawkto_property_id': settings.TAWKTO_PROPERTY_ID,
    }
