"""
Serializers for the Payment Service.

Handles input validation and output representation for payment transactions.
"""

from decimal import Decimal

from rest_framework import serializers


class CreatePaymentSerializer(serializers.Serializer):
    """Validates input for creating a payment transaction."""

    order_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        min_value=Decimal("0.01"),
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
    )


class PaymentStatusHistorySerializer(serializers.Serializer):
    """Output representation for payment status history entries."""

    id = serializers.UUIDField()
    from_status = serializers.CharField()
    to_status = serializers.CharField()
    created_at = serializers.DateTimeField()


class PaymentTransactionSerializer(serializers.Serializer):
    """Output representation for a payment transaction."""

    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    idempotency_key = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    status_history = PaymentStatusHistorySerializer(many=True, read_only=True)
