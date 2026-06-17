from django.urls import path
from .views import OrderCreateView, OrderListView

urlpatterns = [
    path('orders/', OrderCreateView.as_view(), name='order-create'),
    path('stores/<int:store_id>/orders/', OrderListView.as_view(), name='order-list'),
]