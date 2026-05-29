"""
Serializers for the Shipping Service.

Handles input validation and output representation for:
- Shipment creation
- Shipment status updates
- Shipment detail with status history
"""

from rest_framework import serializers

from apps.shipping.models import Shipment, ShipmentStatusHistory


# =============================================================================
# Input Serializers
# =============================================================================


class CreateShipmentSerializer(serializers.Serializer):
    """
    Validates shipment creation input.

    Required fields:
    - order_id: UUID of the associated order
    - shipping_address: delivery address text
    """

    order_id = serializers.UUIDField()
    shipping_address = serializers.CharField(min_length=1, max_length=5000)

    def validate_shipping_address(self, value):
        """Ensure shipping address is not blank after stripping."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Shipping address cannot be blank.")
        return value


class UpdateShipmentStatusSerializer(serializers.Serializer):
    """
    Validates shipment status update input.

    Required fields:
    - status: the new status to transition to
    """

    status = serializers.ChoiceField(
        choices=["processing", "shipping", "delivered"],
    )


# =============================================================================
# Output Serializers
# =============================================================================


class ShipmentStatusHistorySerializer(serializers.ModelSerializer):
    """
    Serializes a single shipment status history entry.
    """

    class Meta:
        model = ShipmentStatusHistory
        fields = ["id", "from_status", "to_status", "created_at"]
        read_only_fields = fields


class ShipmentDetailSerializer(serializers.ModelSerializer):
    """
    Full shipment detail serializer with status history.
    """

    status_history = ShipmentStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "order_id",
            "tracking_code",
            "status",
            "shipping_address",
            "created_at",
            "updated_at",
            "status_history",
        ]
        read_only_fields = fields
