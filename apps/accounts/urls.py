from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('wallet/', views.wallet_view, name='wallet_view'),
    path('wallet/transactions/', views.transactions_view, name='transactions_view'),
    path('wallet/deposit/', views.deposit_request, name='deposit_request'),
    path('wallet/withdrawal/', views.withdrawal_request, name='withdrawal_request'),
    path('wallet/connect/', views.connect_wallet, name='connect_wallet'),
    path('wallet/balances/', views.wallet_balances, name='wallet_balances'),
]
