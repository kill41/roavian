from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/portfolio-data/', views.portfolio_data, name='portfolio_data'),
    path('api/price-ticker/', views.price_ticker, name='price_ticker'),
    path('api/balance-stats/', views.balance_stats, name='balance_stats'),
]
