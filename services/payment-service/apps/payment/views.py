"""
API views for the Payment Service.

Handles HTTP request/response layer with no business logic.
Delegates operations to PaymentService.
All responses use the standard envelope format.
"""

from rest_framework.views import APIView

from apps.core.exceptions import ValidationError
from apps.core.responses import success_response
from apps.payment.serializers import (
    CreatePaymentSerializer,
    PaymentTransactionSerializer,
)
from apps.payment.services import PaymentService


class PaymentCreateView(APIView):
    """
    POST /api/v1/payments/ — Create a payment transaction.

    Requires order_id, amount, and idempotency_key.
    Returns existing transaction if idempotency_key already exists.
    """

    permission_classes = []

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid payment data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        payment_transaction = PaymentService.create_payment(
            order_id=data["order_id"],
            amount=data["amount"],
            idempotency_key=data["idempotency_key"],
        )

        # Reload with status history
        payment_transaction = _reload_with_history(payment_transaction.id)
        output = PaymentTransactionSerializer(payment_transaction).data
        return success_response(output, status=201)


class PaymentSimulateSuccessView(APIView):
    """
    POST /api/v1/payments/{id}/simulate-success/ — Simulate payment success.

    Transitions a pending payment to success and records status history.
    """

    permission_classes = []

    def post(self, request, pk):
        payment_transaction = PaymentService.simulate_success(transaction_id=pk)

        # Reload with status history
        payment_transaction = _reload_with_history(payment_transaction.id)
        output = PaymentTransactionSerializer(payment_transaction).data
        return success_response(output)


class PaymentSimulateFailureView(APIView):
    """
    POST /api/v1/payments/{id}/simulate-failure/ — Simulate payment failure.

    Transitions a pending payment to failed and records status history.
    """

    permission_classes = []

    def post(self, request, pk):
        payment_transaction = PaymentService.simulate_failure(transaction_id=pk)

        # Reload with status history
        payment_transaction = _reload_with_history(payment_transaction.id)
        output = PaymentTransactionSerializer(payment_transaction).data
        return success_response(output)


# =============================================================================
# Private Helpers
# =============================================================================


def _reload_with_history(transaction_id):
    """Reload a payment transaction with its status history prefetched."""
    from apps.payment.models import PaymentTransaction

    return (
        PaymentTransaction.objects.prefetch_related("status_history")
        .get(id=transaction_id)
    )


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
