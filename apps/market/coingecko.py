import requests
import time
from decimal import Decimal
from django.conf import settings


class CoinGeckoClient:
    BASE_URL = settings.COINGECKO_API_URL

    def __init__(self):
        self.session = requests.Session()
        self.params = {}
        if settings.COINGECKO_API_KEY:
            self.params['x_cg_demo_api_key'] = settings.COINGECKO_API_KEY

    def _request(self, url, params):
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=20)
                if resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    def get_coin_markets(self, coin_ids):
        params = {
            'vs_currency': 'usd',
            'ids': ','.join(coin_ids),
            'order': 'market_cap_desc',
            'sparkline': 'false',
            'price_change_percentage': '24h',
            **self.params,
        }
        return self._request(f'{self.BASE_URL}/coins/markets', params)

    def get_ohlc(self, coin_id, days=7):
        params = {'vs_currency': 'usd', 'days': days, **self.params}
        return self._request(f'{self.BASE_URL}/coins/{coin_id}/ohlc', params)
