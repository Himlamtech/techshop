"""
Business logic services for the Shipping Service.

Handles:
- Shipment creation with tracking code generation
- Status transitions with forward-only validation
- Shipment retrieval by order ID
"""

import secrets

from django.db import transaction

from apps.core.exceptions import NotFoundError, ValidationError
from apps.shipping.models import SHIPMENT_TRANSITIONS, Shipment, ShipmentStatusHistory


class ShippingService:
    """
    Service layer for shipment operations.

    All write operations are wrapped in transactions.
    Status transitions are validated against SHIPMENT_TRANSITIONS.
    """

    @staticmethod
    def generate_tracking_code():
        """
        Generate a unique tracking code.

        Format: "TS" + 12 uppercase hex characters = 14 chars total.
        Uses secrets.token_hex(6) for cryptographic randomness.
        """
        return "TS" + secrets.token_hex(6).upper()

    @classmethod
    def create_shipment(cls, order_id, shipping_address):
        """
        Create a new shipment for an order.

        Args:
            order_id: UUID of the associated order.
            shipping_address: Delivery address text.

        Returns:
            The created Shipment instance with status_history prefetched.

        Raises:
            ValidationError: If a shipment already exists for this order.
        """
        # Check for existing shipment for this order
        if Shipment.objects.filter(order_id=order_id).exists():
            raise ValidationError(
                message="A shipment already exists for this order",
                details=[{"field": "order_id", "reason": "Duplicate shipment for order."}],
            )

        tracking_code = cls.generate_tracking_code()

        # Ensure tracking code uniqueness (extremely unlikely collision)
        while Shipment.objects.filter(tracking_code=tracking_code).exists():
            tracking_code = cls.generate_tracking_code()

        with transaction.atomic():
            shipment = Shipment.objects.create(
                order_id=order_id,
                tracking_code=tracking_code,
                status="processing",
                shipping_address=shipping_address,
            )

            # Create initial status history entry
            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                from_status="",
                to_status="processing",
            )

        # Reload with status history for response
        shipment = Shipment.objects.prefetch_related("status_history").get(pk=shipment.pk)
        return shipment

    @classmethod
    def update_status(cls, shipment_id, new_status):
        """
        Update a shipment's status with forward-only transition validation.

        Args:
            shipment_id: UUID of the shipment to update.
            new_status: The target status to transition to.

        Returns:
            The updated Shipment instance with status_history prefetched.

        Raises:
            NotFoundError: If the shipment does not exist.
            ValidationError: If the transition is not allowed.
        """
        try:
            shipment = Shipment.objects.get(pk=shipment_id)
        except Shipment.DoesNotExist:
            raise NotFoundError("Shipment not found")

        current_status = shipment.status
        allowed_transitions = SHIPMENT_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise ValidationError(
                message=f"Invalid status transition from '{current_status}' to '{new_status}'",
                details=[
                    {
                        "field": "status",
                        "reason": f"Transition from '{current_status}' to '{new_status}' is not allowed. "
                        f"Allowed transitions: {allowed_transitions}",
                    }
                ],
            )

        with transaction.atomic():
            shipment.status = new_status
            shipment.save(update_fields=["status", "updated_at"])

            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                from_status=current_status,
                to_status=new_status,
            )

        # Reload with status history for response
        shipment = Shipment.objects.prefetch_related("status_history").get(pk=shipment.pk)
        return shipment

    @classmethod
    def get_by_order(cls, order_id):
        """
        Retrieve a shipment by order ID with status history.

        Args:
            order_id: UUID of the order.

        Returns:
            The Shipment instance with status_history prefetched.

        Raises:
            NotFoundError: If no shipment exists for this order.
        """
        try:
            shipment = (
                Shipment.objects.prefetch_related("status_history").get(order_id=order_id)
            )
        except Shipment.DoesNotExist:
            raise NotFoundError("Shipment not found for this order")

        return shipment
