from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Store, Inventory
from .serializers import InventoryListSerializer

class InventoryListView(APIView):
    """
    GET /stores/<store_id>/inventory/
    Returns all inventory items for a store.
    """

    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)

        # select_related() follows the foreign key chain in a single SQL JOIN.
        # Without it, accessing inv.product.category.name in the serializer
        # would trigger 2 extra database queries per inventory item!
        inventory = (
            Inventory.objects
            .filter(store=store)
            .select_related('product', 'product__category')
            .order_by('product__title')
        )

        return Response(InventoryListSerializer(inventory, many=True).data)