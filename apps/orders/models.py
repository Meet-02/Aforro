from django.db import models

class Order(models.Model):
    class Status(models.Choices):
        PENDING   = 'PENDING'
        CONFIRMED = 'CONFIRMED'
        REJECTED  = 'REJECTED'

    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} [{self.status}]"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items' 
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT
    )
    quantity_requested = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity_requested}x {self.product.title}"