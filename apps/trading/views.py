from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction as db_transaction
from apps.market.models import MarketAsset, OhlcSnapshot, CryptoPriceHistory
from apps.market.coingecko import CoinGeckoClient
from apps.accounts.models import Transaction, UserHolding
from .models import Order
import random
from datetime import timedelta
from django.utils.timezone import now
import time

FEE_RATE = Decimal('0.001')  # 0.1%


@login_required
def trade_view(request, asset_code):
    asset = get_object_or_404(MarketAsset, code=asset_code.upper(), is_active=True)
    account = request.user.account
    holding = UserHolding.objects.filter(account=account, asset=asset).first()
    recent_orders = Order.objects.filter(asset=asset)[:30]
    return render(request, 'trading/trade.html', {
        'asset': asset,
        'account': account,
        'holding': holding,
        'recent_orders': recent_orders,
    })


def generate_order_book(asset):
    price = float(asset.current_price)
    spread = price * 0.0005
    bids = []
    asks = []
    levels = 8
    for i in range(levels):
        offset = spread * (i + 1) * (1 + i * 0.3)
        size = round(random.uniform(0.1, 2.0) / (1 + i * 0.4), 6)
        bids.append({'price': round(price - offset, 2), 'size': size, 'total': round(size * (price - offset), 2)})
        size_a = round(random.uniform(0.1, 2.0) / (1 + i * 0.4), 6)
        asks.append({'price': round(price + offset, 2), 'size': size_a, 'total': round(size_a * (price + offset), 2)})
    return {'bids': bids, 'asks': asks}


@login_required
def order_book_data(request, asset_code):
    asset = get_object_or_404(MarketAsset, code=asset_code.upper())
    ob = generate_order_book(asset)
    return JsonResponse(ob)


@login_required
@require_POST
def execute_order(request, asset_code):
    asset = get_object_or_404(MarketAsset, code=asset_code.upper())
    account = request.user.account
    side = request.POST.get('side', 'BUY').upper()
    order_type = request.POST.get('order_type', 'MARKET').upper()
    amount_input = request.POST.get('amount', '0')
    limit_price_input = request.POST.get('limit_price', None)

    try:
        amount = Decimal(str(amount_input))
    except Exception:
        return HttpResponse('Invalid amount', status=400)
    if amount <= Decimal('0'):
        return HttpResponse('Amount must be positive', status=400)

    if order_type == 'LIMIT':
        try:
            limit_price = Decimal(str(limit_price_input))
        except Exception:
            return HttpResponse('Invalid limit price', status=400)
        if limit_price <= Decimal('0'):
            return HttpResponse('Limit price must be positive', status=400)
        Order.objects.create(
            account=account, asset=asset, side=side,
            order_type='LIMIT', status='PENDING',
            quantity=amount, limit_price=limit_price,
        )
        Transaction.objects.create(
            account=account, type='TRADE_BUY' if side == 'BUY' else 'TRADE_SELL',
            status='PENDING', asset_code=asset.code,
            asset_amount=amount, price_at_trade=float(limit_price),
        )
        return render(request, 'trading/_order_success.html', {
            'side': side, 'asset': asset, 'amount': amount,
            'price': limit_price, 'order_type': 'LIMIT',
            'account': account, 'status': 'PENDING',
        })

    # MARKET order - execute immediately
    exec_price = asset.current_price
    total = (amount * exec_price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    slippage = total * Decimal(str(random.uniform(-0.0005, 0.0005)))
    total += slippage
    fee = (total * FEE_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_with_fee = total + fee

    with db_transaction.atomic():
        if side == 'BUY':
            if account.cash_balance < total_with_fee:
                return HttpResponse(f'Insufficient USD. Need ${total_with_fee}', status=400)
            account.cash_balance -= total_with_fee
            h, _ = UserHolding.objects.get_or_create(account=account, asset=asset,
                defaults={'balance': Decimal('0'), 'average_entry_price': exec_price})
            old_val = h.balance * h.average_entry_price
            new_avg = (old_val + total) / (h.balance + amount) if (h.balance + amount) > 0 else exec_price
            h.balance += amount
            h.average_entry_price = new_avg.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            h.save()
        else:
            h = UserHolding.objects.filter(account=account, asset=asset).first()
            if not h or h.balance < amount:
                return HttpResponse('Insufficient asset balance', status=400)
            pnl = (exec_price - h.average_entry_price) * amount
            h.balance -= amount
            h.save()
            account.cash_balance += total - fee

        account.save()
        Order.objects.create(
            account=account, asset=asset, side=side, order_type='MARKET',
            status='COMPLETED', quantity=amount, filled_quantity=amount,
            price_at_exec=exec_price, total_fiat=total, fee=fee, pnl=pnl if side == 'SELL' else None,
        )
        Transaction.objects.create(
            account=account, type='TRADE_BUY' if side == 'BUY' else 'TRADE_SELL',
            status='COMPLETED', asset_code=asset.code,
            fiat_amount=total, asset_amount=amount, price_at_trade=float(exec_price),
        )

    return render(request, 'trading/_order_success.html', {
        'side': side, 'asset': asset, 'amount': amount,
        'price': exec_price, 'total': total, 'fee': fee,
        'order_type': 'MARKET', 'account': account, 'status': 'COMPLETED',
        'pnl': pnl if side == 'SELL' else None,
    })


@login_required
def candlestick_data(request, asset_code):
    asset = get_object_or_404(MarketAsset, code=asset_code.upper())
    days = int(request.GET.get('days', 7))
    since = now() - timedelta(days=days)
    ohlc = OhlcSnapshot.objects.filter(asset=asset, timestamp__gte=since).order_by('timestamp')
    if ohlc.exists():
        data = [{
            'time': int(o.timestamp.timestamp()),
            'open': float(o.open), 'high': float(o.high),
            'low': float(o.low), 'close': float(o.close),
        } for o in ohlc]
    else:
        history = CryptoPriceHistory.objects.filter(asset=asset, timestamp__gte=since).order_by('timestamp')[:500]
        if history.count() < 2:
            price = float(asset.current_price)
            data = [{'time': int(now().timestamp()) - 86400 * days + i * 3600,
                     'open': price, 'high': price * 1.01, 'low': price * 0.99, 'close': price} for i in range(min(24 * days, 200))]
        else:
            data = []
            for i, h in enumerate(history):
                price = float(h.price_usd)
                data.append({
                    'time': int(h.timestamp.timestamp()),
                    'open': price, 'high': price * 1.005, 'low': price * 0.995, 'close': price,
                })
    return JsonResponse(data, safe=False)
