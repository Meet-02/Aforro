from rest_framework import serializers
from .models import Store, Inventory

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'location']

class InventoryListSerializer(serializers.ModelSerializer):
    """Used specifically for the GET /stores/<id>/inventory/ endpoint."""
    
    # We pull these fields through the foreign keys to flatten the JSON response
    product_title = serializers.CharField(source='product.title')
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    category_name = serializers.CharField(source='product.category.name')

    class Meta:
        model = Inventory
        fields = ['id', 'product_title', 'product_price', 'category_name', 'quantity']