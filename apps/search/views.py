from django.db.models import Q, Case, When, IntegerField, Value
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.products.models import Product
from apps.stores.models import Inventory
from apps.products.serializers import ProductSerializer

class ProductSearchView(APIView):
    """
    GET /api/search/products/
    Supports keyword search, filters, sorting, and pagination.
    Results are cached in Redis for 5 minutes.
    """

    def get(self, request):
        params = request.query_params

        # Build a unique cache key based on the exact search parameters
        cache_key = 'search:' + str(sorted(params.items()))
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        queryset = Product.objects.select_related('category').all()

        # ── Keyword search ────────────────────────────────────────────────────
        q = params.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        # ── Filters ───────────────────────────────────────────────────────────
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

        # ── Sorting ───────────────────────────────────────────────────────────
        sort = params.get('sort', 'relevance')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('title')

        # ── Pagination ────────────────────────────────────────────────────────
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductSerializer(page, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, response_data, timeout=300)

        return Response(response_data)


class AutocompleteView(APIView):
    """
    GET /api/search/suggest/?q=xxx
    Fast prefix-first autocomplete with Redis rate limiting.
    """

    RATE_LIMIT  = 20   # max requests
    RATE_WINDOW = 60   # per 60 seconds

    def get(self, request):
        # ── Rate limiting using Redis ─────────────────────────────────────────
        from django.core.cache import cache as redis_cache

        ip = request.META.get('REMOTE_ADDR', 'unknown')
        rl_key = f'rl:suggest:{ip}'

        count = redis_cache.get(rl_key, 0)
        if count == 0:
            redis_cache.set(rl_key, 1, timeout=self.RATE_WINDOW)
        elif count >= self.RATE_LIMIT:
            return Response(
                {'error': 'Rate limit exceeded. Try again in a minute.'},
                status=429
            )
        else:
            redis_cache.incr(rl_key)

        # ── Input validation ──────────────────────────────────────────────────
        q = request.query_params.get('q', '').strip()
        if len(q) < 3:
            return Response({'error': 'Minimum 3 characters required.'}, status=400)

        # ── Query: Prefix matches first, then general matches ─────────────────
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