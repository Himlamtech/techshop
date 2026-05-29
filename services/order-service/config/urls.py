"""URL configuration for order service."""

from django.contrib import admin
from django.urls import include, path

from apps.core.healthcheck import liveness, readiness
from apps.order.urls import admin_urlpatterns

urlpatterns = [
    path("healthz", liveness, name="healthz"),
    path("readyz", readiness, name="readyz"),
    path("admin/", admin.site.urls),
    path("api/v1/orders/", include("apps.order.urls")),
    path("api/v1/admin/", include(admin_urlpatterns)),
]
