from django.urls import path
from .views import ProductSearchView, AutocompleteView

urlpatterns = [
    path('api/search/products/', ProductSearchView.as_view(), name='product-search'),
    path('api/search/suggest/', AutocompleteView.as_view(), name='autocomplete'),
]