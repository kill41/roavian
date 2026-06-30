from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from apps.market.models import MarketAsset


def dashboard(request):
    if not request.user.is_authenticated:
        features = [
            {'title': 'Decentralized Security', 'desc': 'Your assets protected with multi-layered encryption and cold storage.', 'icon': '<i class="bi bi-shield-check"></i>', 'bg': 'rgba(14,203,129,0.1)'},
            {'title': 'Intuitive Dashboard', 'desc': 'Effortlessly track investments and analyze performance with our streamlined UI.', 'icon': '<i class="bi bi-grid-3x3-gap-fill"></i>', 'bg': 'rgba(55,91,210,0.1)'},
            {'title': 'Real-time Market Data', 'desc': 'Live price feeds from CoinGecko, integrated trading tools, and in-depth analytics.', 'icon': '<i class="bi bi-graph-up-arrow"></i>', 'bg': 'rgba(246,70,93,0.1)'},
            {'title': 'Smart Order Trading', 'desc': 'Market and limit orders with synthetic order book, 0.1% fees, and P&L tracking.', 'icon': '<i class="bi bi-arrow-left-right"></i>', 'bg': 'rgba(139,92,246,0.1)'},
            {'title': 'Wallet Connect', 'desc': 'Connect your wallet with demo seed phrases and manage deposits and withdrawals.', 'icon': '<i class="bi bi-wallet-fill"></i>', 'bg': 'rgba(255,165,0,0.1)'},
            {'title': '29+ Supported Assets', 'desc': 'Trade Bitcoin, Ethereum, Solana, and 26+ top cryptocurrencies with live pricing.', 'icon': '<i class="bi bi-currency-bitcoin"></i>', 'bg': 'rgba(14,203,129,0.1)'},
        ]
        return render(request, 'landing/index.html', {'features': features})

    account = request.user.account
    assets = MarketAsset.objects.filter(is_active=True)

    holdings = account.holdings.select_related('asset').all()
    total_pnl = 0
    best = {'code': '', 'change': -999}
    worst = {'code': '', 'change': 999}
    for h in holdings:
        val = float(h.balance) * float(h.asset.current_price)
        cost = float(h.balance) * float(h.average_entry_price) if h.average_entry_price else 0
        pnl = val - cost
        total_pnl += pnl
        change_pct = ((float(h.asset.current_price) - float(h.average_entry_price)) / float(h.average_entry_price) * 100) if h.average_entry_price and float(h.average_entry_price) > 0 else 0
        if change_pct > best['change']:
            best = {'code': h.asset.code, 'change': change_pct}
        if change_pct < worst['change']:
            worst = {'code': h.asset.code, 'change': change_pct}

    return render(request, 'dashboard/index.html', {
        'account': account,
        'assets': assets,
        'total_pnl': round(total_pnl, 2),
        'best_performer': best,
        'worst_performer': worst,
    })


@login_required
def portfolio_data(request):
    account = request.user.account
    usd_val = float(account.cash_balance)
    labels = ['USD'] if usd_val > 0 else []
    values = [round(usd_val, 2)] if usd_val > 0 else []
    for h in account.holdings.select_related('asset').all():
        val = float(h.balance) * float(h.asset.current_price)
        if val > 0.01:
            labels.append(h.asset.code)
            values.append(round(val, 2))
    return JsonResponse({'labels': labels, 'values': values})


@login_required
def price_ticker(request):
    assets = MarketAsset.objects.filter(is_active=True)
    return render(request, 'includes/price_ticker.html', {'assets': assets})


@login_required
def balance_stats(request):
    account = request.user.account
    holdings = account.holdings.select_related('asset').all()
    total_pnl = 0
    best = {'code': '', 'change': -999}
    for h in holdings:
        val = float(h.balance) * float(h.asset.current_price)
        cost = float(h.balance) * float(h.average_entry_price) if h.average_entry_price else 0
        pnl = val - cost
        total_pnl += pnl
        change_pct = ((float(h.asset.current_price) - float(h.average_entry_price)) / float(h.average_entry_price) * 100) if h.average_entry_price and float(h.average_entry_price) > 0 else 0
        if change_pct > best['change']:
            best = {'code': h.asset.code, 'change': change_pct}
    return render(request, 'includes/balance_stats.html', {
        'account': account,
        'total_pnl': round(total_pnl, 2),
        'best_performer': best,
    })
