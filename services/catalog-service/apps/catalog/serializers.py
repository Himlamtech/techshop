"""
Serializers for the Catalog Service.

Handles input validation and output representation for:
- Categories (hierarchical with nested children)
- Products (list, detail, create, update)
- Product images
- Product import from DummyJSON
- Filter/search query parameters
- Bulk validation
"""

from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Category, Product, ProductImage


# =============================================================================
# Category Serializers
# =============================================================================


class CategorySerializer(serializers.ModelSerializer):
    """
    Category output serializer with nested children support.
    Returns id, name, slug, parent_id, is_active, level, and children list.
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent_id",
            "is_active",
            "level",
            "children",
        ]
        read_only_fields = fields

    def get_children(self, obj):
        """Recursively serialize child categories."""
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


class CategoryCreateSerializer(serializers.Serializer):
    """
    Category creation serializer.
    Validates name and optional parent_id, enforces depth <= 3.
    """

    name = serializers.CharField(min_length=1, max_length=100)
    parent_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_name(self, value):
        """Ensure name is not blank after stripping."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Category name cannot be blank.")
        return value

    def validate_parent_id(self, value):
        """Validate that parent category exists and depth won't exceed 3."""
        if value is None:
            return value

        try:
            parent = Category.objects.get(id=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Parent category does not exist."
            )

        if parent.level >= 3:
            raise serializers.ValidationError(
                "Category depth cannot exceed 3 levels."
            )

        return value


# =============================================================================
# Product Image Serializers
# =============================================================================


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Product image output serializer.
    Returns id, image_url, is_primary, sort_order.
    """

    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "is_primary", "sort_order"]
        read_only_fields = fields


# =============================================================================
# Product Serializers
# =============================================================================


class ProductListSerializer(serializers.ModelSerializer):
    """
    Product list serializer — lightweight representation for listing pages.
    Includes thumbnail_url (primary image) and category name.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "slug",
            "price",
            "stock",
            "brand",
            "category_name",
            "status",
            "rating_avg",
            "rating_count",
            "thumbnail_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_thumbnail_url(self, obj):
        """Return the primary image URL, or the first image, or None."""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image_url
        first = obj.images.first()
        return first.image_url if first else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Product detail serializer — full representation with images and category.
    """

    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "brand",
            "category",
            "status",
            "attributes",
            "rating_avg",
            "rating_count",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProductCreateSerializer(serializers.Serializer):
    """
    Product creation serializer with full field validation.

    Validates:
    - name: 1-255 characters
    - description: 1-5000 characters
    - price: 0.01 to 999,999,999.99
    - stock: 0 to 999,999
    - brand: 1-100 characters
    - category_id: must reference an existing active category
    - image_urls: list with at least 1 URL
    - attributes: optional JSON object
    """

    name = serializers.CharField(min_length=1, max_length=255)
    description = serializers.CharField(min_length=1, max_length=5000)
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("999999999.99"),
    )
    stock = serializers.IntegerField(min_value=0, max_value=999999)
    brand = serializers.CharField(min_length=1, max_length=100)
    category_id = serializers.UUIDField()
    image_urls = serializers.ListField(
        child=serializers.URLField(max_length=2048),
        min_length=1,
        max_length=20,
    )
    attributes = serializers.JSONField(required=False, allow_null=True)

    def validate_name(self, value):
        """Ensure name is not blank after stripping."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Product name cannot be blank.")
        return value

    def validate_brand(self, value):
        """Ensure brand is not blank after stripping."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Brand cannot be blank.")
        return value

    def validate_category_id(self, value):
        """Validate that the category exists and is active."""
        try:
            category = Category.objects.get(id=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")

        if not category.is_active:
            raise serializers.ValidationError("Category is not active.")

        return value


class ProductUpdateSerializer(serializers.Serializer):
    """
    Product partial update serializer.
    All fields are optional for PATCH operations.

    Validates same ranges as ProductCreateSerializer where applicable.
    """

    name = serializers.CharField(min_length=1, max_length=255, required=False)
    description = serializers.CharField(
        min_length=1, max_length=5000, required=False
    )
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("999999999.99"),
        required=False,
    )
    stock = serializers.IntegerField(
        min_value=0, max_value=999999, required=False
    )
    brand = serializers.CharField(min_length=1, max_length=100, required=False)
    status = serializers.ChoiceField(
        choices=["active", "inactive"], required=False
    )
    attributes = serializers.JSONField(required=False, allow_null=True)

    def validate_name(self, value):
        """Ensure name is not blank after stripping."""
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError(
                    "Product name cannot be blank."
                )
        return value

    def validate_brand(self, value):
        """Ensure brand is not blank after stripping."""
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Brand cannot be blank.")
        return value


# =============================================================================
# Product Import Serializer (DummyJSON)
# =============================================================================


class ProductImportSerializer(serializers.Serializer):
    """
    Maps DummyJSON product fields to our internal product format.

    DummyJSON fields → Internal fields:
    - title → name
    - thumbnail → primary image
    - images → additional images
    - price → price
    - stock → stock
    - category → category (matched by name/slug)
    - brand → brand
    - description → description
    - id → sku (prefixed with 'DUMMY-')
    """

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(
        max_length=5000, required=False, default=""
    )
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("999999999.99"),
    )
    stock = serializers.IntegerField(min_value=0, max_value=999999)
    brand = serializers.CharField(max_length=100, required=False, default="")
    category = serializers.CharField(max_length=100, required=False, default="")
    thumbnail = serializers.URLField(
        max_length=2048, required=False, allow_blank=True
    )
    images = serializers.ListField(
        child=serializers.URLField(max_length=2048),
        required=False,
        default=list,
    )
    id = serializers.IntegerField()

    def to_internal_value(self, data):
        """Map DummyJSON fields to internal representation."""
        validated = super().to_internal_value(data)

        # Build the internal product representation
        sku = f"DUMMY-{validated['id']}"
        name = validated["title"]

        # Collect image URLs: thumbnail as primary, images as additional
        image_urls = []
        thumbnail = validated.get("thumbnail", "")
        if thumbnail:
            image_urls.append(thumbnail)

        additional_images = validated.get("images", [])
        for img_url in additional_images:
            if img_url and img_url not in image_urls:
                image_urls.append(img_url)

        return {
            "sku": sku,
            "name": name,
            "description": validated.get("description", ""),
            "price": validated["price"],
            "stock": validated["stock"],
            "brand": validated.get("brand", ""),
            "category_name": validated.get("category", ""),
            "image_urls": image_urls,
            "thumbnail_url": thumbnail,
        }


# =============================================================================
# Filter/Search Query Parameter Serializers
# =============================================================================


class ProductFilterSerializer(serializers.Serializer):
    """
    Validates and parses query parameters for product listing/search.

    Supported parameters:
    - search: keyword search (min 2 chars)
    - category: category slug filter
    - brand: brand name filter
    - min_price: minimum price filter
    - max_price: maximum price filter
    - min_rating: minimum average rating filter
    - sort: sort option (price_asc, price_desc, rating, newest)
    - page: page number
    - page_size: items per page (max 50 for product listing)
    """

    SORT_CHOICES = [
        ("price_asc", "Price: Low to High"),
        ("price_desc", "Price: High to Low"),
        ("rating", "Highest Rated"),
        ("newest", "Newest First"),
    ]

    search = serializers.CharField(
        min_length=2, max_length=200, required=False, allow_blank=True
    )
    category = serializers.SlugField(max_length=120, required=False)
    brand = serializers.CharField(max_length=100, required=False)
    min_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )
    max_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    min_rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        min_value=Decimal("0.0"),
        max_value=Decimal("5.0"),
        required=False,
    )
    sort = serializers.ChoiceField(
        choices=[c[0] for c in SORT_CHOICES],
        required=False,
        default="newest",
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(
        min_value=1, max_value=50, required=False, default=20
    )

    def validate(self, attrs):
        """Cross-field validation for price range."""
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise serializers.ValidationError(
                    {"max_price": "max_price must be greater than or equal to min_price."}
                )

        # Remove blank search
        search = attrs.get("search", "")
        if search is not None and search.strip() == "":
            attrs.pop("search", None)

        return attrs


# =============================================================================
# Bulk Validation Serializer
# =============================================================================


class BulkValidateSerializer(serializers.Serializer):
    """
    Accepts a list of product_ids for bulk validation.
    Used by Cart and Order services to verify product availability.
    """

    product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
    )
