from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation(self, order_id):
    try:
        from apps.orders.models import Order

        order = Order.objects.prefetch_related('items__product').get(pk=order_id)

        logger.info(
            f"[ORDER CONFIRMATION] Order #{order.id} | "
            f"Store: {order.store.name} | "
            f"Status: {order.status} | "
            f"Items: {order.items.count()}"
        )

        if order.status == 'CONFIRMED':
            logger.info(f"  ✓ Stock deducted successfully for order #{order.id}")
        else:
            logger.info(f"  ✗ Order #{order.id} rejected — insufficient stock")

    except Exception as exc:
        raise self.retry(exc=exc)