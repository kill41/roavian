from decimal import Decimal
from django import template

register = template.Library()


@register.simple_tag
def crypto_balance(account, code):
    try:
        h = account.holdings.select_related('asset').get(asset__code=code)
        val = h.balance
        if val == val.to_integral_value():
            return f'{val:.8f}'
        return f'{val:f}'
    except Exception:
        return '0.00000000'


@register.simple_tag
def crypto_value_usd(account, code):
    from apps.market.models import MarketAsset
    try:
        asset = MarketAsset.objects.get(code=code)
        h = account.holdings.get(asset=asset)
        val = h.balance * asset.current_price
        return f'{val:.2f}'
    except Exception:
        return '0.00'
