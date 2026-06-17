from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
import random

from apps.products.models import Category, Product
from apps.stores.models import Store, Inventory

fake = Faker()

class Command(BaseCommand):
    help = 'Seeds the database with realistic test data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        with transaction.atomic():
            categories = self._create_categories()
            products   = self._create_products(categories)
            stores     = self._create_stores()
            self._create_inventory(stores, products)

        self.stdout.write(self.style.SUCCESS('Done! Database seeded successfully.'))

    def _create_categories(self):
        self.stdout.write('  Creating categories...')
        names = [
            'Electronics', 'Clothing', 'Food & Beverages', 'Books',
            'Sports & Outdoors', 'Home & Garden', 'Toys & Games',
            'Health & Beauty', 'Automotive', 'Office Supplies',
            'Music & Instruments', 'Pet Supplies',
        ]
        categories = []
        for name in names:
            cat, _ = Category.objects.get_or_create(name=name)
            categories.append(cat)
        self.stdout.write(f'    Created {len(categories)} categories')
        return categories

    def _create_products(self, categories):
        self.stdout.write('  Creating 1000 products...')
        Product.objects.all().delete()

        products = [
            Product(
                title=fake.catch_phrase(),
                description=fake.paragraph(nb_sentences=3),
                price=round(random.uniform(1.99, 999.99), 2),
                category=random.choice(categories),
            )
            for _ in range(1000)
        ]
        created = Product.objects.bulk_create(products, batch_size=200)
        self.stdout.write(f'    Created {len(created)} products')
        return created

    def _create_stores(self):
        self.stdout.write('  Creating 20 stores...')
        Store.objects.all().delete()

        stores = [
            Store(
                name=fake.company(),
                location=fake.city()
            )
            for _ in range(20)
        ]
        created = Store.objects.bulk_create(stores)
        self.stdout.write(f'    Created {len(created)} stores')
        return created

    def _create_inventory(self, stores, products):
        self.stdout.write('  Creating inventory (300 products per store)...')
        Inventory.objects.all().delete()

        inventory_rows = []
        for store in stores:
            # Pick 300 random products for this store
            selected = random.sample(list(products), 300)
            for product in selected:
                inventory_rows.append(Inventory(
                    store=store,
                    product=product,
                    quantity=random.randint(0, 200),
                ))

        Inventory.objects.bulk_create(inventory_rows, batch_size=500)
        self.stdout.write(f'    Created {len(inventory_rows)} inventory rows')