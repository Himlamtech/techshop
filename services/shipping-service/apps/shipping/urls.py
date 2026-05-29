"""
URL routing for the Shipping Service API.

All endpoints are prefixed with /api/v1/ (configured in config/urls.py).

Endpoints:
- POST   /shipments/                    — Create shipment for an order
- PATCH  /shipments/<uuid:pk>/status/   — Staff update shipment status
- GET    /shipments/order/<uuid:order_id>/ — Get shipment by order ID
"""

from django.urls import path

from apps.shipping.views import (
    ShipmentByOrderView,
    ShipmentCreateView,
    ShipmentStatusUpdateView,
)

urlpatterns = [
    path("shipments/", ShipmentCreateView.as_view(), name="shipment-create"),
    path(
        "shipments/<uuid:pk>/status/",
        ShipmentStatusUpdateView.as_view(),
        name="shipment-status-update",
    ),
    path(
        "shipments/order/<uuid:order_id>/",
        ShipmentByOrderView.as_view(),
        name="shipment-by-order",
    ),
]
