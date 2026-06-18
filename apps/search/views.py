from django.db.models import Q, Case, When, IntegerField, Value
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.products.models import Product
from apps.stores.models import Inventory
from apps.products.serializers import ProductSerializer


class ProductSearchView(APIView):

    @extend_schema(
        summary='Search products',
        parameters=[
            OpenApiParameter('q',         OpenApiTypes.STR,  description='Keyword (searches title, description, category)'),
            OpenApiParameter('category',  OpenApiTypes.STR,  description='Filter by category name'),
            OpenApiParameter('min_price', OpenApiTypes.DECIMAL, description='Minimum price'),
            OpenApiParameter('max_price', OpenApiTypes.DECIMAL, description='Maximum price'),
            OpenApiParameter('store_id',  OpenApiTypes.INT,  description='Only products stocked at this store'),
            OpenApiParameter('sort',      OpenApiTypes.STR,  description='price_asc | price_desc | newest | relevance'),
            OpenApiParameter('page',      OpenApiTypes.INT,  description='Page number'),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request):
        params = request.query_params

        cache_key = 'search:' + str(sorted(params.items()))
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        queryset = Product.objects.select_related('category').all()

        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        category = params.get('category')
        if category:
            queryset = queryset.filter(category__name__icontains=category)

        min_price = params.get('min_price')
        max_price = params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        store_id = params.get('store_id')
        if store_id:
            stocked_product_ids = Inventory.objects.filter(
                store_id=store_id,
                quantity__gt=0
            ).values_list('product_id', flat=True)
            queryset = queryset.filter(id__in=stocked_product_ids)

        sort = params.get('sort', 'relevance')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('title')

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductSerializer(page, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        cache.set(cache_key, response_data, timeout=300)

        return Response(response_data)


class AutocompleteView(APIView):

    RATE_LIMIT  = 20
    RATE_WINDOW = 60

    @extend_schema(
        summary='Autocomplete product titles',
        parameters=[
            OpenApiParameter('q', OpenApiTypes.STR, required=True, description='Min 3 characters. Rate limited to 20 req/min.'),
        ],
        responses={200: {'type': 'object', 'properties': {'results': {'type': 'array', 'items': {'type': 'string'}}}}},
    )
    def get(self, request):
        from django.core.cache import cache as redis_cache

        ip = request.META.get('REMOTE_ADDR', 'unknown')
        rl_key = f'rl:suggest:{ip}'

        count = redis_cache.get(rl_key, 0)
        if count == 0:
            redis_cache.set(rl_key, 1, timeout=self.RATE_WINDOW)
        elif count >= self.RATE_LIMIT:
            return Response({'error': 'Rate limit exceeded. Try again in a minute.'}, status=429)
        else:
            redis_cache.incr(rl_key)

        q = request.query_params.get('q', '').strip()
        if len(q) < 3:
            return Response({'error': 'Minimum 3 characters required.'}, status=400)

        queryset = (
            Product.objects
            .filter(title__icontains=q)
            .annotate(
                sort_priority=Case(
                    When(title__istartswith=q, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            )
            .order_by('sort_priority', 'title')
            .values_list('title', flat=True)[:10]
        )

        return Response({'results': list(queryset)})