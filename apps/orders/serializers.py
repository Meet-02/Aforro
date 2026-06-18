from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField(min_value=1)

class OrderCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    items = OrderItemInputSerializer(many=True, min_length=1)

class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_title', 'quantity_requested']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)  # 

    class Meta:
        model = Order
        fields = ['id', 'store_id', 'status', 'created_at', 'item_count', 'items']