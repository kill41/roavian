from django.urls import path
from . import views

urlpatterns = [
    path('<str:asset_code>/', views.trade_view, name='trade'),
    path('<str:asset_code>/execute/', views.execute_order, name='execute_order'),
    path('<str:asset_code>/candlestick-data/', views.candlestick_data, name='candlestick_data'),
]
