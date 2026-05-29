"""
URL routing for the Payment Service API.

All endpoints are prefixed with /api/v1/ (configured in config/urls.py).

Endpoints:
- POST /payments/                          — Create payment transaction
- POST /payments/<uuid:pk>/simulate-success/ — Simulate payment success
- POST /payments/<uuid:pk>/simulate-failure/ — Simulate payment failure
"""

from django.urls import path

from apps.payment.views import (
    PaymentCreateView,
    PaymentSimulateFailureView,
    PaymentSimulateSuccessView,
)

urlpatterns = [
    path("payments/", PaymentCreateView.as_view(), name="payment-create"),
    path(
        "payments/<uuid:pk>/simulate-success/",
        PaymentSimulateSuccessView.as_view(),
        name="payment-simulate-success",
    ),
    path(
        "payments/<uuid:pk>/simulate-failure/",
        PaymentSimulateFailureView.as_view(),
        name="payment-simulate-failure",
    ),
]
