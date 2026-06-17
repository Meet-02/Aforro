from django.core.management.base import BaseCommand
from django.db import transaction
import random

from apps.products.models import Category, Product
from apps.stores.models import Store, Inventory

class Command(BaseCommand):
    help = 'Seeds the database with basic grocery products'

    def handle(self, *args, **kwargs):
        self.stdout.write('🛒 Seeding basic grocery products...')

        grocery_data = {
            'Produce': [
                ('Organic Bananas', 0.99), ('Gala Apples', 1.49), ('Avocados (2-pack)', 3.00),
                ('Baby Spinach', 3.50), ('Carrots 1kg', 1.20), ('Garlic', 0.50),
                ('Red Onions', 1.10), ('Roma Tomatoes', 2.00)
            ],
            'Dairy & Eggs': [
                ('Whole Milk 1L', 2.50), ('Large Brown Eggs (12)', 3.20), ('Salted Butter', 4.00),
                ('Cheddar Cheese Block', 5.50), ('Greek Yogurt', 1.50)
            ],
            'Bakery': [
                ('Whole Wheat Bread', 2.99), ('Sourdough Loaf', 4.50), ('Everything Bagels (6)', 3.00),
                ('Croissants (4)', 4.00)
            ],
            'Pantry': [
                ('Extra Virgin Olive Oil', 8.99), ('Basmati Rice 1kg', 4.50), ('Penne Pasta', 1.80),
                ('Tomato Basil Sauce', 2.20), ('Peanut Butter', 3.50), ('Sea Salt', 1.50),
                ('Black Beans', 1.10), ('All-Purpose Flour', 2.50)
            ],
            'Beverages': [
                ('Ground Coffee', 7.99), ('Green Tea Bags', 4.50), ('Orange Juice', 3.50),
                ('Sparkling Water (12-pack)', 5.20)
            ]
        }

        with transaction.atomic():
            # 1. Create a dedicated Grocery Store
            store, _ = Store.objects.get_or_create(
                name="Aforro Fresh Market",
                defaults={'location': 'Mumbai Central'}
            )

            created_products = []

            # 2. Create Categories and Products
            for cat_name, items in grocery_data.items():
                category, _ = Category.objects.get_or_create(name=cat_name)

                for title, price in items:
                    product, created = Product.objects.get_or_create(
                        title=title,
                        defaults={
                            'description': f'Fresh, high-quality {title.lower()} for your daily needs.',
                            'price': price,
                            'category': category
                        }
                    )
                    created_products.append(product)

            # 3. Stock the inventory
            for product in created_products:
                # Use get_or_create so we can run this multiple times without crashing
                inv, created = Inventory.objects.get_or_create(
                    store=store,
                    product=product,
                    defaults={'quantity': random.randint(50, 300)}
                )
                if not created:
                    # If it already exists, just add more stock
                    inv.quantity += random.randint(20, 100)
                    inv.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Done! {len(created_products)} grocery items are now stocked at {store.name}.'))