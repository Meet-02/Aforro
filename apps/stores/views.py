from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from .models import Store, Inventory
from .serializers import InventoryListSerializer


class InventoryListView(APIView):

    @extend_schema(
        summary='List inventory for a store',
        responses={200: InventoryListSerializer(many=True)},
    )
    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)
        inventory = (
            Inventory.objects
            .filter(store=store)
            .select_related('product', 'product__category')
            .order_by('product__title')
        )

        return Response(InventoryListSerializer(inventory, many=True).data)