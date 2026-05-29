"""
API views for the Order Service.

Handles HTTP request/response layer with no business logic.
All responses use the standard envelope format.
"""

from django.db.models import Count, Sum
from rest_framework.views import APIView

from apps.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAdmin, IsAuthenticated, IsCustomer
from apps.core.responses import success_response
from apps.order.models import ORDER_TRANSITIONS, Order, OrderStatusHistory
from apps.order.serializers import (
    CancelOrderInputSerializer,
    CheckoutInputSerializer,
    OrderDetailOutputSerializer,
    OrderListOutputSerializer,
    OrderOutputSerializer,
)
from apps.order.services import OrderService


class CheckoutView(APIView):
    """
    POST /api/v1/orders/checkout — Orchestrate the full checkout workflow:
    get cart → validate items → create order → process payment → create shipment.
    """

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CheckoutInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid request data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        service = OrderService(
            authorization_header=request.META.get("HTTP_AUTHORIZATION")
        )
        order_data = service.checkout(
            user_id=str(request.user_id),
            shipping_address=data["shipping_address"],
        )
        output_serializer = OrderOutputSerializer(order_data)
        return success_response(output_serializer.data, status=201)


class OrderListView(APIView):
    """
    GET /api/v1/orders — Paginated list of orders.

    - Customer: sees only their own orders.
    - Staff/Admin: sees all orders.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = request.user_id

        # Customer sees only own orders; staff/admin see all
        queryset = Order.objects.all()
        if user_role == "customer":
            queryset = queryset.filter(user_id=user_id)

        # Annotate with item count for the list serializer
        queryset = queryset.annotate(item_count=Count("items"))

        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)

        # Serialize
        serializer = OrderListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class OrderDetailView(APIView):
    """
    GET /api/v1/orders/{id} — Order detail with items and status history.

    - Customer: can only view own orders (FORBIDDEN otherwise).
    - Staff/Admin: can view any order.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.prefetch_related("items", "status_history").get(pk=pk)
        except Order.DoesNotExist:
            raise NotFoundError("Order not found")

        # Ownership check for customers
        user_role = getattr(request, "user_role", None)
        if user_role == "customer" and str(order.user_id) != str(request.user_id):
            raise ForbiddenError(
                "You do not have permission to access this resource"
            )

        # Build output data
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status,
            "subtotal": order.subtotal,
            "shipping_fee": order.shipping_fee,
            "discount_amount": order.discount_amount,
            "total_amount": order.total_amount,
            "shipping_address": order.shipping_address,
            "items": list(order.items.all().values(
                "id", "product_id", "product_name", "product_sku",
                "product_image_url", "unit_price", "quantity", "line_total",
            )),
            "status_history": list(order.status_history.all().values(
                "id", "from_status", "to_status", "reason", "created_at",
            )),
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }

        serializer = OrderDetailOutputSerializer(order_data)
        return success_response(serializer.data)


class OrderCancelView(APIView):
    """
    PATCH /api/v1/orders/{id}/cancel — Cancel an order.

    - Customer: can only cancel own orders.
    - Staff/Admin: can cancel any order.
    - Validates that the transition to 'cancelled' is allowed from the current status.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            raise NotFoundError("Order not found")

        # Ownership check for customers
        user_role = getattr(request, "user_role", None)
        if user_role == "customer" and str(order.user_id) != str(request.user_id):
            raise ForbiddenError(
                "You do not have permission to access this resource"
            )

        # Validate cancel reason input
        serializer = CancelOrderInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid request data",
                details=_format_serializer_errors(serializer.errors),
            )

        # Validate status transition
        current_status = order.status
        allowed_transitions = ORDER_TRANSITIONS.get(current_status, set())
        if "cancelled" not in allowed_transitions:
            raise ValidationError(
                message=(
                    f"Cannot cancel order in '{current_status}' status. "
                    f"Allowed transitions from '{current_status}': "
                    f"{sorted(allowed_transitions) if allowed_transitions else 'none (terminal status)'}"
                ),
            )

        # Perform the cancellation
        reason = serializer.validated_data.get("reason", "")
        from_status = order.status
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])

        # Create status history entry
        OrderStatusHistory.objects.create(
            order=order,
            from_status=from_status,
            to_status="cancelled",
            reason=reason or None,
        )

        # Return updated order detail
        order.refresh_from_db()
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status,
            "subtotal": order.subtotal,
            "shipping_fee": order.shipping_fee,
            "discount_amount": order.discount_amount,
            "total_amount": order.total_amount,
            "shipping_address": order.shipping_address,
            "items": list(order.items.all().values(
                "id", "product_id", "product_name", "product_sku",
                "product_image_url", "unit_price", "quantity", "line_total",
            )),
            "status_history": list(order.status_history.all().values(
                "id", "from_status", "to_status", "reason", "created_at",
            )),
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }

        serializer = OrderDetailOutputSerializer(order_data)
        return success_response(serializer.data)


# =============================================================================
# Admin Views
# =============================================================================


class AdminOrderStatsView(APIView):
    """
    GET /api/v1/admin/stats — Admin dashboard statistics for orders.

    Returns total orders, orders grouped by status, and total revenue
    (sum of total_amount for paid and completed orders).
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        total_orders = Order.objects.count()

        # Orders grouped by status
        status_counts = (
            Order.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        orders_by_status = {item["status"]: item["count"] for item in status_counts}

        # Total revenue from paid and completed orders
        revenue = Order.objects.filter(
            status__in=["paid", "completed"]
        ).aggregate(total_revenue=Sum("total_amount"))

        total_revenue = str(revenue["total_revenue"] or "0.00")

        return success_response({
            "total_orders": total_orders,
            "orders_by_status": orders_by_status,
            "total_revenue": total_revenue,
        })


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
