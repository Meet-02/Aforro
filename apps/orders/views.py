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
    """
    POST /orders/
    Creates an order for a store.
    - CONFIRMED if all items have enough stock (stock is deducted)
    - REJECTED  if any item has insufficient stock (nothing is deducted)
    The entire operation runs inside transaction.atomic().
    """

    def post(self, request):
        # Step 1: Validate input shape
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        store_id = data['store_id']
        items = data['items']

        store = get_object_or_404(Store, pk=store_id)

        # Step 2: Wrap everything in an atomic transaction.
        # If anything raises an exception, the DB rolls back to the state
        # before this block — no partial writes.
        with transaction.atomic():

            # Step 3: Lock the inventory rows we need.
            # select_for_update() adds a "FOR UPDATE" clause to the SQL.
            product_ids = [item['product_id'] for item in items]

            inventory_map = {
                inv.product_id: inv
                for inv in Inventory.objects.select_for_update().filter(
                    store=store,
                    product_id__in=product_ids
                )
            }

            # Step 4: Check stock for every requested item
            insufficient = []
            for item in items:
                pid = item['product_id']
                qty = item['quantity_requested']
                inv = inventory_map.get(pid)

                if inv is None or inv.quantity < qty:
                    insufficient.append(pid)

            # Step 5: Create the order
            # Step 5: Create the order
            order_status = Order.Status.REJECTED.value if insufficient else Order.Status.CONFIRMED.value
            order = Order.objects.create(store=store, status=order_status)

            # Step 6: Create order items and deduct stock only if CONFIRMED
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

        # Step 7: Fire async Celery task AFTER the transaction commits.
        send_order_confirmation.delay(order.id)

        # Step 8: Return the full order with annotated item_count
        order_with_count = Order.objects.annotate(
            item_count=Count('items')
        ).get(pk=order.pk)

        return Response(
            OrderSerializer(order_with_count).data,
            status=status.HTTP_201_CREATED
        )


class OrderListView(APIView):
    """
    GET /stores/<store_id>/orders/
    Returns all orders for a store, newest first.
    Uses annotate() to add item_count without N+1 queries.
    """

    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)

        # annotate() adds a calculated field to each row in a single SQL query.
        orders = (
            Order.objects
            .filter(store=store)
            .annotate(item_count=Count('items'))
            .prefetch_related('items__product')  # pre-loads items in one query
            .order_by('-created_at')
        )

        return Response(OrderSerializer(orders, many=True).data)