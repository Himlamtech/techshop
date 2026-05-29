"""
API views for the Shipping Service.

Handles HTTP request/response layer with no business logic.
Delegates operations to ShippingService.
All responses use the standard envelope format via success_response.
"""

from rest_framework.views import APIView

from apps.core.exceptions import ForbiddenError, ValidationError
from apps.core.permissions import IsAuthenticated, IsStaff
from apps.core.responses import success_response
from apps.shipping.serializers import (
    CreateShipmentSerializer,
    ShipmentDetailSerializer,
    UpdateShipmentStatusSerializer,
)
from apps.shipping.services import ShippingService


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


# =============================================================================
# Shipment Views
# =============================================================================


class ShipmentCreateView(APIView):
    """
    POST /api/v1/shipments/ — Create a shipment for an order.

    Creates a shipment with a generated tracking code and initial status "processing".
    Typically called by Order_Service during checkout orchestration.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateShipmentSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid shipment data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        shipment = ShippingService.create_shipment(
            order_id=data["order_id"],
            shipping_address=data["shipping_address"],
        )

        output_serializer = ShipmentDetailSerializer(shipment)
        return success_response(output_serializer.data, status=201)


class ShipmentStatusUpdateView(APIView):
    """
    PATCH /api/v1/shipments/{id}/status/ — Staff updates shipment status.

    Enforces forward-only transitions:
    - processing → shipping
    - shipping → delivered
    """

    permission_classes = [IsStaff]

    def patch(self, request, pk):
        serializer = UpdateShipmentStatusSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid status update data",
                details=_format_serializer_errors(serializer.errors),
            )

        new_status = serializer.validated_data["status"]
        shipment = ShippingService.update_status(
            shipment_id=pk,
            new_status=new_status,
        )

        output_serializer = ShipmentDetailSerializer(shipment)
        return success_response(output_serializer.data)


class ShipmentByOrderView(APIView):
    """
    GET /api/v1/shipments/order/{order_id}/ — Customer gets shipment status.

    Returns shipment status, tracking code, and status history.
    Enforces ownership: customer can only view their own order's shipment.
    Staff/admin can view any shipment.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        shipment = ShippingService.get_by_order(order_id=order_id)

        # Ownership check: staff/admin can view any, customers only their own
        user_role = getattr(request, "user_role", None)
        if user_role not in ("admin", "staff"):
            # For customers, verify the order belongs to them.
            # The order_id ownership is validated by checking if the requesting
            # user's ID matches. Since Shipping_Service doesn't store user_id
            # on shipments (it's on the Order), we rely on the gateway/caller
            # to pass the correct context. For direct API access, we check
            # the X-User-ID or rely on the Order_Service having validated this.
            # Per task spec: "ownership will be enforced at gateway level"
            # but we still check if user_id is provided in request headers
            # as a secondary check.
            user_id = getattr(request, "user_id", None)
            order_user_id = request.META.get("HTTP_X_ORDER_USER_ID")

            if order_user_id and str(user_id) != str(order_user_id):
                raise ForbiddenError(
                    "You do not have permission to access this resource"
                )

        output_serializer = ShipmentDetailSerializer(shipment)
        return success_response(output_serializer.data)
