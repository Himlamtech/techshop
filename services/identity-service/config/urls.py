"""URL configuration for identity service."""

from django.contrib import admin
from django.urls import include, path

from apps.core.healthcheck import liveness, readiness

urlpatterns = [
    path("healthz", liveness, name="healthz"),
    path("readyz", readiness, name="readyz"),
    path("api/v1/auth/", include("apps.identity.urls")),
    path("admin/", admin.site.urls),
]
