from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.stores.models import Store, Inventory
from apps.products.models import Product
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer
from .tasks import send_order_confirmation


class OrderCreateView(APIView):

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        store_id = data['store_id']
        items = data['items']

        store = get_object_or_404(Store, pk=store_id)

        with transaction.atomic():

            product_ids = [item['product_id'] for item in items]

            inventory_map = {
                inv.product_id: inv
                for inv in Inventory.objects.select_for_update().filter(
                    store=store,
                    product_id__in=product_ids
                )
            }

            insufficient = []
            for item in items:
                pid = item['product_id']
                qty = item['quantity_requested']
                inv = inventory_map.get(pid)

                if inv is None or inv.quantity < qty:
                    insufficient.append(pid)

            order_status = Order.Status.REJECTED.value if insufficient else Order.Status.CONFIRMED.value
            order = Order.objects.create(store=store, status=order_status)

            order_items = []
            for item in items:
                order_items.append(OrderItem(
                    order=order,
                    product_id=item['product_id'],
                    quantity_requested=item['quantity_requested'],
                ))

            OrderItem.objects.bulk_create(order_items)

            if order_status == Order.Status.CONFIRMED.value:
                for item in items:
                    inv = inventory_map[item['product_id']]
                    inv.quantity -= item['quantity_requested']
                    inv.save()
    
        send_order_confirmation.delay(order.id)

        order_with_count = Order.objects.annotate(
            item_count=Count('items')
        ).get(pk=order.pk)

        return Response(
            OrderSerializer(order_with_count).data,
            status=status.HTTP_201_CREATED
        )


class OrderListView(APIView):

    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)

        orders = (
            Order.objects
            .filter(store=store)
            .annotate(item_count=Count('items'))
            .prefetch_related('items__product') 
            .order_by('-created_at')
        )

        return Response(OrderSerializer(orders, many=True).data)