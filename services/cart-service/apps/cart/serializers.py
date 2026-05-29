"""
Serializers for Cart Service.

Handles input validation and output representation for cart endpoints.
"""

from decimal import Decimal

from rest_framework import serializers


class AddCartItemSerializer(serializers.Serializer):
    """Validates input for adding an item to the cart."""

    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(required=False, default=1, min_value=1, max_value=99)


class UpdateCartItemSerializer(serializers.Serializer):
    """Validates input for updating a cart item's quantity."""

    quantity = serializers.IntegerField(required=True, min_value=1, max_value=99)


class CartItemOutputSerializer(serializers.Serializer):
    """Output representation for a single cart item with product info."""

    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    thumbnail = serializers.CharField(allow_null=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity = serializers.IntegerField()
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class CartOutputSerializer(serializers.Serializer):
    """Output representation for the full cart with items and subtotal."""

    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    items = CartItemOutputSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
