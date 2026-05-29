import uuid

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    URLValidator,
)
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """
    Hierarchical product category with up to 3 levels of nesting.
    """

    LEVEL_CHOICES = [(1, "Level 1"), (2, "Level 2"), (3, "Level 3")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Enforce level based on parent
        if self.parent is None:
            self.level = 1
        else:
            self.level = self.parent.level + 1
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        # Enforce max depth of 3 levels
        if self.parent is not None and self.parent.level >= 3:
            raise ValidationError(
                {"parent": "Category depth cannot exceed 3 levels."}
            )


class Product(models.Model):
    """
    Product in the catalog with pricing, stock, and metadata.
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(max_length=5000, blank=True, default="")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(999999999.99),
        ],
    )
    stock = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(999999),
        ],
    )
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )
    attributes = models.JSONField(null=True, blank=True)
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0),
        ],
    )
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="idx_product_status_created"),
            models.Index(fields=["category"], name="idx_product_category"),
            models.Index(fields=["brand"], name="idx_product_brand"),
            models.Index(fields=["price"], name="idx_product_price"),
            models.Index(fields=["-rating_avg"], name="idx_product_rating"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug uniqueness by appending SKU if needed
            if Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{self.sku.lower()}"
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """
    Product image with primary designation and ordering.
    Constraints:
    - Exactly one is_primary per product
    - Maximum 20 images per product
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_url = models.URLField(max_length=2048, validators=[URLValidator()])
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order"]
        constraints = [
            # Ensure exactly one primary image per product using a partial unique index
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Image for {self.product.name} (primary={self.is_primary})"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Enforce max 20 images per product
        if not self.pk:  # Only check on creation
            existing_count = ProductImage.objects.filter(product=self.product).count()
            if existing_count >= 20:
                raise ValidationError(
                    "A product cannot have more than 20 images."
                )
