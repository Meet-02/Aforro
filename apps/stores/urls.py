from django.urls import path
from .views import InventoryListView

urlpatterns = [
    path('stores/<int:store_id>/inventory/', InventoryListView.as_view(), name='inventory-list'),
]