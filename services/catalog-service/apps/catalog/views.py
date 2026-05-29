"""
API views for the Catalog Service.

Handles HTTP request/response layer with no business logic.
Delegates queries to selectors and writes to model operations.
All responses use the standard envelope format via success_response/error_response.
"""

from django.core.management import call_command
from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify
from rest_framework.views import APIView

from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.selectors import (
    get_categories_tree,
    get_product_detail,
    get_product_list,
    get_products_by_category,
    validate_products_bulk,
)
from apps.catalog.serializers import (
    BulkValidateSerializer,
    CategoryCreateSerializer,
    CategorySerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductFilterSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
)
from apps.core.exceptions import NotFoundError, ValidationError
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAdmin
from apps.core.responses import error_response, success_response


# =============================================================================
# Product Views
# =============================================================================


class ProductListView(APIView):
    """
    GET  /api/v1/products/ — Public paginated product list with filters and sorting.
    POST /api/v1/products/ — Admin create product with images.
    """

    permission_classes = []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return []

    def get(self, request):
        filter_serializer = ProductFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            raise ValidationError(
                message="Invalid filter parameters",
                details=_format_serializer_errors(filter_serializer.errors),
            )

        filters = filter_serializer.validated_data
        queryset = get_product_list(filters)

        # Paginate
        paginator = StandardPagination()
        paginator.page_size = filters.get("page_size", 20)
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid product data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        image_urls = data.pop("image_urls")

        with transaction.atomic():
            # Create product
            product = Product.objects.create(
                name=data["name"],
                description=data["description"],
                price=data["price"],
                stock=data["stock"],
                brand=data["brand"],
                category_id=data["category_id"],
                attributes=data.get("attributes"),
            )

            # Create images — first one is primary
            for i, url in enumerate(image_urls):
                ProductImage.objects.create(
                    product=product,
                    image_url=url,
                    is_primary=(i == 0),
                    sort_order=i,
                )

        # Reload with relations for response
        product = (
            Product.objects.select_related("category")
            .prefetch_related("images")
            .get(pk=product.pk)
        )
        output_serializer = ProductDetailSerializer(product)
        return success_response(output_serializer.data, status=201)


class ProductDetailView(APIView):
    """
    GET    /api/v1/products/{id}/ — Public full product detail with images and attributes.
    PATCH  /api/v1/products/{id}/ — Admin update product fields.
    DELETE /api/v1/products/{id}/ — Admin soft-delete (set status=inactive).
    """

    permission_classes = []

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAdmin()]
        return []

    def get(self, request, pk):
        product = get_product_detail(pk)
        if product is None:
            raise NotFoundError("Product not found")

        serializer = ProductDetailSerializer(product)
        return success_response(serializer.data)

    def patch(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise NotFoundError("Product not found")

        serializer = ProductUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid update data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        for field, value in data.items():
            setattr(product, field, value)
        product.save()

        # Reload with relations for response
        product = (
            Product.objects.select_related("category")
            .prefetch_related("images")
            .get(pk=product.pk)
        )
        output_serializer = ProductDetailSerializer(product)
        return success_response(output_serializer.data)

    def delete(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise NotFoundError("Product not found")

        product.status = "inactive"
        product.save(update_fields=["status", "updated_at"])

        return success_response({"id": str(product.id), "status": "inactive"})


class ProductBulkValidateView(APIView):
    """
    POST /api/v1/products/validate-bulk/ — Internal endpoint for cart/order validation.
    """

    permission_classes = []

    def post(self, request):
        serializer = BulkValidateSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid request data",
                details=_format_serializer_errors(serializer.errors),
            )

        product_ids = serializer.validated_data["product_ids"]
        results = validate_products_bulk(product_ids)
        return success_response(results)


class ProductImportView(APIView):
    """
    POST /api/v1/products/import/ — Admin trigger DummyJSON product import.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        limit = request.data.get("limit", 30)

        try:
            limit = int(limit)
            if limit < 1 or limit > 194:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValidationError(
                message="Invalid limit parameter",
                details=[{"field": "limit", "reason": "Must be an integer between 1 and 194."}],
            )

        try:
            call_command("seed_products", limit=limit)
        except SystemExit:
            return error_response(
                code="SERVICE_UNAVAILABLE",
                message="Failed to import products from DummyJSON API",
                status=503,
            )

        return success_response(
            {"message": f"Product import triggered successfully with limit={limit}"},
            status=200,
        )


# =============================================================================
# Category Views
# =============================================================================


class CategoryListView(APIView):
    """
    GET  /api/v1/categories/ — Public list of all active categories with hierarchy.
    POST /api/v1/categories/ — Admin create category with slug generation.
    """

    permission_classes = []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return []

    def get(self, request):
        categories = get_categories_tree()
        serializer = CategorySerializer(categories, many=True)
        return success_response(serializer.data)

    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(
                message="Invalid category data",
                details=_format_serializer_errors(serializer.errors),
            )

        data = serializer.validated_data
        name = data["name"]
        parent_id = data.get("parent_id")

        # Generate slug
        slug = slugify(name)

        # Check for duplicate slug
        if Category.objects.filter(slug=slug).exists():
            raise ValidationError(
                message="A category with this name already exists",
                details=[{"field": "name", "reason": "Category name must be unique."}],
            )

        # Determine level and parent
        parent = None
        level = 1
        if parent_id:
            parent = Category.objects.get(id=parent_id)
            level = parent.level + 1

        category = Category.objects.create(
            name=name,
            slug=slug,
            parent=parent,
            level=level,
            is_active=True,
        )

        output_serializer = CategorySerializer(category)
        return success_response(output_serializer.data, status=201)


class CategoryProductsView(APIView):
    """
    GET /api/v1/categories/{slug}/products/ — Public products by category including subcategories.
    """

    permission_classes = []

    def get(self, request, slug):
        queryset, category = get_products_by_category(slug)
        if queryset is None:
            raise NotFoundError("Category not found")

        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# Admin Views
# =============================================================================


class AdminStatsView(APIView):
    """
    GET /api/v1/admin/stats — Admin dashboard statistics for the catalog.

    Returns total products, active products, total categories,
    and product counts grouped by category.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        total_products = Product.objects.count()
        active_products = Product.objects.filter(status="active").count()
        total_categories = Category.objects.filter(is_active=True).count()

        products_by_category = (
            Category.objects.filter(is_active=True)
            .annotate(count=Count("products"))
            .values("name", "count")
            .order_by("-count")
        )

        return success_response({
            "total_products": total_products,
            "active_products": active_products,
            "total_categories": total_categories,
            "products_by_category": [
                {"name": item["name"], "count": item["count"]}
                for item in products_by_category
            ],
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
