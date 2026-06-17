from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.products.models import Category, Product
from apps.stores.models import Store, Inventory
from apps.orders.models import Order

class OrderCreationTests(TestCase):
    """Tests for POST /orders/"""

    def setUp(self):
        """Create baseline data used by every test in this class."""
        self.client = APIClient()

        self.category = Category.objects.create(name='Electronics')
        self.store    = Store.objects.create(name='Test Store', location='Mumbai')

        self.product_a = Product.objects.create(
            title='Laptop', price=999.99, category=self.category
        )
        self.product_b = Product.objects.create(
            title='Mouse', price=29.99, category=self.category
        )

        # Stock: 5 Laptops, 10 Mice
        Inventory.objects.create(store=self.store, product=self.product_a, quantity=5)
        Inventory.objects.create(store=self.store, product=self.product_b, quantity=10)

        self.url = '/orders/'

    def test_order_confirmed_when_stock_sufficient(self):
        """Requesting items within stock limits creates a CONFIRMED order."""
        payload = {
            'store_id': self.store.id,
            'items': [
                {'product_id': self.product_a.id, 'quantity_requested': 2},
                {'product_id': self.product_b.id, 'quantity_requested': 3},
            ]
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'CONFIRMED')

        # Verify stock was actually deducted
        self.assertEqual(Inventory.objects.get(product=self.product_a).quantity, 3)
        self.assertEqual(Inventory.objects.get(product=self.product_b).quantity, 7)

    def test_order_rejected_when_stock_insufficient(self):
        """Requesting more than available stock creates a REJECTED order."""
        payload = {
            'store_id': self.store.id,
            'items': [
                {'product_id': self.product_a.id, 'quantity_requested': 999},  # only 5 in stock
            ]
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REJECTED')

        # Verify stock was NOT deducted
        self.assertEqual(Inventory.objects.get(product=self.product_a).quantity, 5)

    def test_partial_insufficient_stock_rejects_entire_order(self):
        """If even ONE item has insufficient stock, the whole order is rejected."""
        payload = {
            'store_id': self.store.id,
            'items': [
                {'product_id': self.product_a.id, 'quantity_requested': 2},   # OK
                {'product_id': self.product_b.id, 'quantity_requested': 999}, # FAILS
            ]
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.data['status'], 'REJECTED')
        # Neither item's stock should be touched (transaction.atomic rolled it back!)
        self.assertEqual(Inventory.objects.get(product=self.product_a).quantity, 5)
        self.assertEqual(Inventory.objects.get(product=self.product_b).quantity, 10)


class InventoryListTests(TestCase):
    """Tests for GET /stores/<id>/inventory/"""

    def setUp(self):
        self.client   = APIClient()
        self.category = Category.objects.create(name='Books')
        self.store    = Store.objects.create(name='Book Store', location='Delhi')

        p1 = Product.objects.create(title='Zebra Guide', price=15.0, category=self.category)
        p2 = Product.objects.create(title='Alpha Manual', price=20.0, category=self.category)

        Inventory.objects.create(store=self.store, product=p1, quantity=8)
        Inventory.objects.create(store=self.store, product=p2, quantity=12)

    def test_inventory_sorted_alphabetically(self):
        """Inventory items must be sorted by product title A→Z."""
        url = f'/stores/{self.store.id}/inventory/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        titles = [item['product_title'] for item in response.data]
        self.assertEqual(titles, sorted(titles))

    def test_inventory_contains_required_fields(self):
        """Each inventory item must include title, price, category, and quantity."""
        url = f'/stores/{self.store.id}/inventory/'
        response = self.client.get(url)

        item = response.data[0]
        self.assertIn('product_title', item)
        self.assertIn('product_price', item)
        self.assertIn('category_name', item)
        self.assertIn('quantity', item)


class AutocompleteTests(TestCase):
    """Tests for GET /api/search/suggest/"""

    def setUp(self):
        self.client   = APIClient()
        category = Category.objects.create(name='Tech')
        Product.objects.create(title='Laptop Pro', price=1000, category=category)
        Product.objects.create(title='Laptop Air', price=800,  category=category)
        Product.objects.create(title='Wireless Headphones', price=200, category=category)

    def test_requires_minimum_3_characters(self):
        """Queries shorter than 3 chars must return 400."""
        response = self.client.get('/api/search/suggest/?q=la')
        self.assertEqual(response.status_code, 400)

    def test_returns_matching_titles(self):
        """Valid query returns matching product titles."""
        response = self.client.get('/api/search/suggest/?q=Lap')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)