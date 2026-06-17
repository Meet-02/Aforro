from django.db import models

class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Inventory(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('store', 'product')

    def __str__(self):
        return f"{self.store.name} — {self.product.title} ({self.quantity})"