"""URL configuration for shipping service."""

from django.contrib import admin
from django.urls import include, path

from apps.core.healthcheck import liveness, readiness

urlpatterns = [
    path("healthz", liveness, name="healthz"),
    path("readyz", readiness, name="readyz"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.shipping.urls")),
]
