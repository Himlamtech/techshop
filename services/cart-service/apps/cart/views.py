"""
API views for the Cart Service.

Handles HTTP request/response layer with no business logic.
Delegates all operations to CartService.
All responses use the standard envelope format.
"""

from rest_framework.views import APIView

from apps.cart.serializers import (
    AddCartItemSerializer,
    CartOutputSerializer,
    UpdateCartItemSerializer,
)
from apps.cart.services import CartService
from apps.core.exceptions import ValidationError
from apps.core.permissions import IsCustomer
from apps.core.responses import success_response


class CartDetailView(APIView):
    """
    GET /api/v1/cart/current — Return the current user's cart with items,
    product info, and subtotal.
    """

    permission_classes = [IsCustomer]

    def get(self, request):
        service = CartService(
            authorization_header=request.META.get("HTTP_AUTHORIZATION")
        )
        cart_data = service.get_cart_detail(request.user_id)
        serializer = CartOutputSerializer(cart_data)
        return success_response(serializer.data)


class CartItemListView(APIView):
    """
    POST /api/v1/cart/items — Add an item to the cart.
    Validates product is active and in-stock via Catalog Service.
    """

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid request data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        service = CartService(
            authorization_header=request.META.get("HTTP_AUTHORIZATION")
        )
        cart_data = service.add_item(
            user_id=request.user_id,
            product_id=str(data["product_id"]),
            quantity=data["quantity"],
        )
        output_serializer = CartOutputSerializer(cart_data)
        return success_response(output_serializer.data, status=201)


class CartItemDetailView(APIView):
    """
    PATCH  /api/v1/cart/items/{id} — Update item quantity (1-99, validate stock).
    DELETE /api/v1/cart/items/{id} — Remove item, return updated cart.
    """

    permission_classes = [IsCustomer]

    def patch(self, request, pk):
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid request data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        service = CartService(
            authorization_header=request.META.get("HTTP_AUTHORIZATION")
        )
        cart_data = service.update_item_quantity(
            user_id=request.user_id,
            item_id=str(pk),
            quantity=data["quantity"],
        )
        output_serializer = CartOutputSerializer(cart_data)
        return success_response(output_serializer.data)

    def delete(self, request, pk):
        service = CartService(
            authorization_header=request.META.get("HTTP_AUTHORIZATION")
        )
        cart_data = service.remove_item(
            user_id=request.user_id,
            item_id=str(pk),
        )
        output_serializer = CartOutputSerializer(cart_data)
        return success_response(output_serializer.data)


# =============================================================================
# Private Helpers
# =============================================================================


def _format_serializer_errors(errors):
    """Convert DRF serializer errors to list of {field, reason} dicts."""
    details = []
    for field, messages in errors.items():
        if isinstance(messages, list):
            for msg in messages:
                details.append({"field": field, "reason": str(msg)})
        else:
            details.append({"field": field, "reason": str(messages)})
    return details
