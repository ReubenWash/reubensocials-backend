# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('wallet/balance/', views.get_wallet_balance, name='wallet-balance'),
    path('wallet/transactions/', views.get_wallet_transactions, name='wallet-transactions'),
    path('payments/add-funds/', views.create_add_funds_intent, name='add-funds'),
    path('payments/confirm/', views.confirm_payment, name='confirm-payment'),
    path('payments/history/', views.get_purchase_history, name='purchase-history'),
]