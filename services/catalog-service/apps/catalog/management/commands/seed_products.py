"""
Management command to seed products from DummyJSON API.

Usage:
    python manage.py seed_products
    python manage.py seed_products --limit 50
    python manage.py seed_products --source dummyjson --limit 100
"""

import sys

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.catalog.models import Category, Product, ProductImage


DUMMYJSON_API_URL = "https://dummyjson.com/products"
DEFAULT_LIMIT = 30
MIN_LIMIT = 1
MAX_LIMIT = 194
REQUEST_TIMEOUT = 30  # seconds

# Price multiplier to convert USD to VND for demo purposes
VND_MULTIPLIER = 1_000_000


class Command(BaseCommand):
    help = "Seed products from DummyJSON API into the catalog database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=DEFAULT_LIMIT,
            help=f"Number of products to fetch (range {MIN_LIMIT}-{MAX_LIMIT}, default {DEFAULT_LIMIT})",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="dummyjson",
            choices=["dummyjson"],
            help='Data source to fetch from (default "dummyjson")',
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        source = options["source"]

        # Validate limit range
        if limit < MIN_LIMIT or limit > MAX_LIMIT:
            self.stderr.write(
                self.style.ERROR(
                    f"Error: --limit must be between {MIN_LIMIT} and {MAX_LIMIT}. Got {limit}."
                )
            )
            sys.exit(1)

        self.stdout.write(
            f"Seeding products from {source} (limit={limit})..."
        )

        if source == "dummyjson":
            self._seed_from_dummyjson(limit)

    def _seed_from_dummyjson(self, limit):
        """Fetch products from DummyJSON API and seed into the database."""
        url = f"{DUMMYJSON_API_URL}?limit={limit}"

        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            self.stderr.write(
                self.style.ERROR(
                    f"Error: Unable to connect to DummyJSON API at {DUMMYJSON_API_URL}. "
                    "Please check your network connection."
                )
            )
            sys.exit(1)
        except requests.exceptions.Timeout:
            self.stderr.write(
                self.style.ERROR(
                    f"Error: Request to DummyJSON API timed out after {REQUEST_TIMEOUT} seconds."
                )
            )
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            self.stderr.write(
                self.style.ERROR(
                    f"Error: DummyJSON API returned HTTP {e.response.status_code}."
                )
            )
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            self.stderr.write(
                self.style.ERROR(
                    f"Error: Failed to fetch from DummyJSON API: {e}"
                )
            )
            sys.exit(1)

        data = response.json()
        products = data.get("products", [])

        if not products:
            self.stdout.write(self.style.WARNING("No products returned from API."))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in products:
            try:
                result = self._process_product(item)
                if result == "created":
                    created_count += 1
                elif result == "updated":
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Warning: Failed to process product '{item.get('title', 'unknown')}': {e}"
                    )
                )
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count}, Updated {updated_count}, "
                f"Skipped {skipped_count} products"
            )
        )

    def _process_product(self, item):
        """
        Process a single product from DummyJSON response.

        Returns: "created", "updated", or "skipped"
        """
        product_id = item.get("id")
        if product_id is None:
            return "skipped"

        # Generate SKU from DummyJSON product ID
        sku = f"TECH-{product_id:04d}"

        # Find or create category
        category_name = item.get("category", "uncategorized")
        category = self._get_or_create_category(category_name)

        # Map DummyJSON fields to our model fields
        name = item.get("title", "")[:255]
        description = item.get("description", "")[:5000]
        price = item.get("price", 0) * VND_MULTIPLIER
        stock = min(item.get("stock", 0), 999999)
        brand = item.get("brand", "Unknown")[:100]
        thumbnail = item.get("thumbnail", "")
        images = item.get("images", [])

        # Generate slug
        slug = slugify(name)

        # Check if product with this SKU already exists
        existing_product = Product.objects.filter(sku=sku).first()

        if existing_product:
            # Update existing product (idempotent)
            existing_product.name = name
            existing_product.description = description
            existing_product.price = price
            existing_product.stock = stock
            existing_product.brand = brand
            existing_product.category = category
            existing_product.status = "active"
            # Update slug only if name changed
            if slugify(name) != existing_product.slug:
                new_slug = slugify(name)
                if Product.objects.filter(slug=new_slug).exclude(pk=existing_product.pk).exists():
                    new_slug = f"{new_slug}-{sku.lower()}"
                existing_product.slug = new_slug
            existing_product.save()

            # Update images
            self._sync_product_images(existing_product, thumbnail, images)
            return "updated"
        else:
            # Ensure slug uniqueness
            if Product.objects.filter(slug=slug).exists():
                slug = f"{slug}-{sku.lower()}"

            # Create new product
            product = Product.objects.create(
                sku=sku,
                name=name,
                slug=slug,
                description=description,
                price=price,
                stock=stock,
                brand=brand,
                category=category,
                status="active",
            )

            # Create images
            self._sync_product_images(product, thumbnail, images)
            return "created"

    def _get_or_create_category(self, category_name):
        """Find or create a top-level category by name."""
        slug = slugify(category_name)
        if not slug:
            slug = "uncategorized"
            category_name = "Uncategorized"

        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": category_name.title(),
                "level": 1,
                "is_active": True,
            },
        )
        return category

    def _sync_product_images(self, product, thumbnail, images):
        """
        Sync product images: set thumbnail as primary, additional images as non-primary.
        Removes existing images and recreates them for idempotent behavior.
        """
        # Remove existing images for this product
        ProductImage.objects.filter(product=product).delete()

        sort_order = 0

        # Add thumbnail as primary image
        if thumbnail:
            ProductImage.objects.create(
                product=product,
                image_url=thumbnail,
                is_primary=True,
                sort_order=sort_order,
            )
            sort_order += 1

        # Add additional images (up to 19 more to stay within 20 max)
        for img_url in images[:19]:
            # Skip if same as thumbnail
            if img_url == thumbnail:
                continue
            ProductImage.objects.create(
                product=product,
                image_url=img_url,
                is_primary=False,
                sort_order=sort_order,
            )
            sort_order += 1
