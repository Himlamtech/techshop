import uuid

from django.core.validators import MaxLengthValidator
from django.db import models


class OrderStatus(models.TextChoices):
    CREATED = "created", "Created"
    PAYMENT_PENDING = "payment_pending", "Payment Pending"
    PAID = "paid", "Paid"
    PAYMENT_FAILED = "payment_failed", "Payment Failed"
    SHIPPING = "shipping", "Shipping"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


# Allowed state transitions for order status lifecycle.
# Terminal statuses (completed, cancelled) have no outgoing transitions.
ORDER_TRANSITIONS = {
    "created": {"payment_pending", "cancelled"},
    "payment_pending": {"paid", "payment_failed", "cancelled"},
    "paid": {"shipping", "cancelled"},
    "shipping": {"completed"},
    "payment_failed": {"payment_pending", "cancelled"},
}


class Order(models.Model):
    """
    Represents a customer order with price totals and lifecycle status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} ({self.status})"


class OrderItem(models.Model):
    """
    Line item in an order. Stores a price snapshot of the product at order time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    product_image_url = models.URLField(max_length=500)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "order_items"
        ordering = ["id"]

    def __str__(self):
        return f"OrderItem({self.product_name}, qty={self.quantity})"


class OrderStatusHistory(models.Model):
    """
    Audit log for order status transitions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        null=True,
        blank=True,
    )
    to_status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
    )
    reason = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        validators=[MaxLengthValidator(500)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"StatusHistory({self.from_status} → {self.to_status})"
