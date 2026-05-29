"""
URL routing for the Catalog Service API.

All endpoints are prefixed with /api/v1/ (configured in config/urls.py).

Endpoints:
- GET    /products/                        — Paginated product list with filters
- POST   /products/                        — Admin create product
- GET    /products/<uuid:pk>/              — Product detail
- PATCH  /products/<uuid:pk>/              — Admin update product
- DELETE /products/<uuid:pk>/              — Admin soft-delete product
- POST   /products/validate-bulk/          — Internal bulk validation
- POST   /products/import/                 — Admin trigger DummyJSON import
- GET    /categories/                      — List active categories (tree)
- POST   /categories/                      — Admin create category
- GET    /categories/<slug:slug>/products/ — Products by category
- GET    /admin/stats                      — Admin catalog statistics
"""

from django.urls import path

from apps.catalog.views import (
    AdminStatsView,
    CategoryListView,
    CategoryProductsView,
    ProductBulkValidateView,
    ProductDetailView,
    ProductImportView,
    ProductListView,
)

urlpatterns = [
    # Admin endpoints
    path("admin/stats", AdminStatsView.as_view(), name="admin-stats"),
    # Product endpoints — validate-bulk and import must come before <uuid:pk> to avoid conflicts
    path("products/validate-bulk/", ProductBulkValidateView.as_view(), name="product-validate-bulk"),
    path("products/import/", ProductImportView.as_view(), name="product-import"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<uuid:pk>/", ProductDetailView.as_view(), name="product-detail"),
    # Category endpoints
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/products/", CategoryProductsView.as_view(), name="category-products"),
]
