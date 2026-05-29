"""
Business logic for the Payment Service.

Handles payment transaction creation, idempotency checks,
and status transitions with history recording.
"""

import logging

from django.db import transaction

from apps.core.exceptions import NotFoundError, ValidationError
from apps.payment.models import PaymentStatusHistory, PaymentTransaction

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class encapsulating payment business logic."""

    @staticmethod
    def create_payment(order_id, amount, idempotency_key):
        """
        Create a new payment transaction or return existing one if idempotency_key matches.

        Args:
            order_id: UUID of the associated order.
            amount: Decimal payment amount.
            idempotency_key: Unique key to ensure idempotent requests.

        Returns:
            PaymentTransaction instance (existing or newly created).
        """
        # Check for existing transaction with same idempotency_key
        existing = PaymentTransaction.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing:
            logger.info(
                "Idempotent payment request detected",
                extra={
                    "idempotency_key": idempotency_key,
                    "transaction_id": str(existing.id),
                },
            )
            return existing

        # Create new transaction with pending status
        with transaction.atomic():
            payment_transaction = PaymentTransaction.objects.create(
                order_id=order_id,
                amount=amount,
                status=PaymentTransaction.Status.PENDING,
                idempotency_key=idempotency_key,
            )

            # Record initial status history
            PaymentStatusHistory.objects.create(
                transaction=payment_transaction,
                from_status="",
                to_status=PaymentTransaction.Status.PENDING,
            )

        logger.info(
            "Payment transaction created",
            extra={
                "transaction_id": str(payment_transaction.id),
                "order_id": str(order_id),
                "amount": str(amount),
            },
        )

        return payment_transaction

    @staticmethod
    def simulate_success(transaction_id):
        """
        Transition a payment transaction from pending to success.

        Args:
            transaction_id: UUID of the payment transaction.

        Returns:
            Updated PaymentTransaction instance.

        Raises:
            NotFoundError: If transaction does not exist.
            ValidationError: If transaction is not in pending status.
        """
        try:
            payment_transaction = PaymentTransaction.objects.get(id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            raise NotFoundError("Payment transaction not found")

        if payment_transaction.status != PaymentTransaction.Status.PENDING:
            raise ValidationError(
                message=f"Cannot transition from '{payment_transaction.status}' to 'success'. Only pending transactions can be completed.",
                details=[
                    {
                        "field": "status",
                        "reason": f"Current status is '{payment_transaction.status}', expected 'pending'.",
                    }
                ],
            )

        with transaction.atomic():
            from_status = payment_transaction.status
            payment_transaction.status = PaymentTransaction.Status.SUCCESS
            payment_transaction.save(update_fields=["status", "updated_at"])

            PaymentStatusHistory.objects.create(
                transaction=payment_transaction,
                from_status=from_status,
                to_status=PaymentTransaction.Status.SUCCESS,
            )

        logger.info(
            "Payment transaction succeeded",
            extra={
                "transaction_id": str(transaction_id),
                "from_status": from_status,
                "to_status": PaymentTransaction.Status.SUCCESS,
            },
        )

        return payment_transaction

    @staticmethod
    def simulate_failure(transaction_id):
        """
        Transition a payment transaction from pending to failed.

        Args:
            transaction_id: UUID of the payment transaction.

        Returns:
            Updated PaymentTransaction instance.

        Raises:
            NotFoundError: If transaction does not exist.
            ValidationError: If transaction is not in pending status.
        """
        try:
            payment_transaction = PaymentTransaction.objects.get(id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            raise NotFoundError("Payment transaction not found")

        if payment_transaction.status != PaymentTransaction.Status.PENDING:
            raise ValidationError(
                message=f"Cannot transition from '{payment_transaction.status}' to 'failed'. Only pending transactions can be failed.",
                details=[
                    {
                        "field": "status",
                        "reason": f"Current status is '{payment_transaction.status}', expected 'pending'.",
                    }
                ],
            )

        with transaction.atomic():
            from_status = payment_transaction.status
            payment_transaction.status = PaymentTransaction.Status.FAILED
            payment_transaction.save(update_fields=["status", "updated_at"])

            PaymentStatusHistory.objects.create(
                transaction=payment_transaction,
                from_status=from_status,
                to_status=PaymentTransaction.Status.FAILED,
            )

        logger.info(
            "Payment transaction failed",
            extra={
                "transaction_id": str(transaction_id),
                "from_status": from_status,
                "to_status": PaymentTransaction.Status.FAILED,
            },
        )

        return payment_transaction
