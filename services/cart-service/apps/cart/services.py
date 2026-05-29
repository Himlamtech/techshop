"""
Business logic for Cart Service.

Handles cart operations including product validation via Catalog Service.
"""

import logging
from decimal import Decimal

from django.conf import settings

from apps.cart.models import Cart, CartItem
from apps.core.exceptions import (
    NotFoundError,
    ProductOutOfStockError,
    ServiceUnavailableError,
    ValidationError,
)
from apps.core.http_client import ServiceClient

logger = logging.getLogger(__name__)


class CartService:
    """Service layer for cart operations."""

    def __init__(self, authorization_header: str | None = None):
        """
        Initialize CartService with optional authorization header for
        inter-service calls.

        Args:
            authorization_header: The Authorization header value from the
                                  incoming request, propagated to catalog calls.
        """
        self._catalog_client = ServiceClient(
            settings.CATALOG_SERVICE_URL, timeout_seconds=3.0
        )
        self._auth_header = authorization_header

    def _get_catalog_headers(self) -> dict | None:
        """Build headers for catalog service calls."""
        if self._auth_header:
            return {"Authorization": self._auth_header}
        return None

    def get_or_create_cart(self, user_id: str) -> Cart:
        """
        Get the existing cart for a user, or create one if it doesn't exist.

        Args:
            user_id: UUID string of the authenticated user.

        Returns:
            Cart instance.
        """
        cart, _ = Cart.objects.get_or_create(user_id=user_id)
        return cart

    def add_item(self, user_id: str, product_id: str, quantity: int = 1) -> dict:
        """
        Add an item to the user's cart after validating with Catalog Service.

        If the product already exists in the cart, the quantity is updated
        (set to the new value, not incremented).

        Args:
            user_id: UUID string of the authenticated user.
            product_id: UUID string of the product to add.
            quantity: Desired quantity (1-99).

        Returns:
            Cart detail dict with items and subtotal.

        Raises:
            ProductOutOfStockError: If product is inactive or insufficient stock.
            ServiceUnavailableError: If Catalog Service is unreachable.
        """
        # Validate product via Catalog Service
        product_info = self._validate_product(product_id, quantity)

        # Get or create cart
        cart = self.get_or_create_cart(user_id)

        # Add or update item
        cart_item, created = CartItem.objects.update_or_create(
            cart=cart,
            product_id=product_id,
            defaults={"quantity": quantity},
        )

        return self.get_cart_detail(user_id)

    def update_item_quantity(
        self, user_id: str, item_id: str, quantity: int
    ) -> dict:
        """
        Update the quantity of a cart item after validating stock.

        Args:
            user_id: UUID string of the authenticated user.
            item_id: UUID string of the cart item to update.
            quantity: New quantity (1-99).

        Returns:
            Cart detail dict with items and subtotal.

        Raises:
            NotFoundError: If cart item doesn't exist or doesn't belong to user.
            ProductOutOfStockError: If insufficient stock.
            ServiceUnavailableError: If Catalog Service is unreachable.
        """
        # Get the cart item, ensuring it belongs to the user's cart
        cart_item = self._get_user_cart_item(user_id, item_id)

        # Validate stock via Catalog Service
        self._validate_product(str(cart_item.product_id), quantity)

        # Update quantity
        cart_item.quantity = quantity
        cart_item.save(update_fields=["quantity", "updated_at"])

        return self.get_cart_detail(user_id)

    def remove_item(self, user_id: str, item_id: str) -> dict:
        """
        Remove an item from the user's cart.

        Args:
            user_id: UUID string of the authenticated user.
            item_id: UUID string of the cart item to remove.

        Returns:
            Cart detail dict with items and subtotal.

        Raises:
            NotFoundError: If cart item doesn't exist or doesn't belong to user.
        """
        cart_item = self._get_user_cart_item(user_id, item_id)
        cart_item.delete()

        return self.get_cart_detail(user_id)

    def get_cart_detail(self, user_id: str) -> dict:
        """
        Get the full cart detail with product info from Catalog Service.

        Returns cart items with product_id, name, thumbnail, unit_price,
        quantity, line_total, and the cart subtotal.

        Args:
            user_id: UUID string of the authenticated user.

        Returns:
            Dict with cart id, user_id, items list, and subtotal.
        """
        cart = self.get_or_create_cart(user_id)
        items = list(cart.items.all())

        if not items:
            return {
                "id": str(cart.id),
                "user_id": str(cart.user_id),
                "items": [],
                "subtotal": Decimal("0.00"),
            }

        # Fetch product info from Catalog Service
        product_ids = [str(item.product_id) for item in items]
        product_map = self._get_products_info(product_ids)

        # Build response items
        cart_items = []
        subtotal = Decimal("0.00")

        for item in items:
            product_id_str = str(item.product_id)
            product_info = product_map.get(product_id_str, {})

            name = product_info.get("name", "Unknown Product")
            thumbnail = product_info.get("image_url")
            unit_price = Decimal(product_info.get("price", "0.00"))
            line_total = unit_price * item.quantity

            cart_items.append({
                "id": str(item.id),
                "product_id": product_id_str,
                "name": name,
                "thumbnail": thumbnail,
                "unit_price": unit_price,
                "quantity": item.quantity,
                "line_total": line_total,
            })
            subtotal += line_total

        return {
            "id": str(cart.id),
            "user_id": str(cart.user_id),
            "items": cart_items,
            "subtotal": subtotal,
        }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _validate_product(self, product_id: str, quantity: int) -> dict:
        """
        Validate a product via Catalog Service's bulk validation endpoint.

        Args:
            product_id: UUID string of the product.
            quantity: Requested quantity.

        Returns:
            Product info dict from catalog validation.

        Raises:
            ProductOutOfStockError: If product is inactive, not found, or
                                    insufficient stock.
            ServiceUnavailableError: If Catalog Service is unreachable.
        """
        try:
            response = self._catalog_client.post(
                "/api/v1/products/validate-bulk/",
                headers=self._get_catalog_headers(),
                json={"product_ids": [product_id]},
            )
        except ServiceUnavailableError:
            raise

        # Parse response — catalog returns standard envelope
        results = response.get("data", [])
        if not results:
            raise ProductOutOfStockError(
                message="Product not found or unavailable"
            )

        product_info = results[0]

        if not product_info.get("valid"):
            reason = product_info.get("reason", "unknown")
            if reason == "not_found":
                raise ProductOutOfStockError(
                    message="Product not found or unavailable"
                )
            elif reason == "inactive":
                raise ProductOutOfStockError(
                    message="Product is inactive and cannot be added to cart"
                )
            elif reason == "out_of_stock":
                raise ProductOutOfStockError(
                    message="Product is out of stock"
                )
            else:
                raise ProductOutOfStockError(
                    message="Product is not available"
                )

        # Check if requested quantity exceeds stock
        stock = product_info.get("stock", 0)
        if quantity > stock:
            raise ProductOutOfStockError(
                message=f"Insufficient stock. Requested: {quantity}, available: {stock}"
            )

        return product_info

    def _get_products_info(self, product_ids: list[str]) -> dict:
        """
        Fetch product info for multiple products from Catalog Service.

        Args:
            product_ids: List of product UUID strings.

        Returns:
            Dict mapping product_id to product info dict.
            Returns empty info for products that fail validation.
        """
        if not product_ids:
            return {}

        try:
            response = self._catalog_client.post(
                "/api/v1/products/validate-bulk/",
                headers=self._get_catalog_headers(),
                json={"product_ids": product_ids},
            )
        except ServiceUnavailableError:
            # If catalog is unavailable for cart display, return empty info
            # so the cart can still be shown with limited product details
            logger.warning(
                "Catalog service unavailable when fetching product info for cart display"
            )
            return {}

        results = response.get("data", [])
        return {item["product_id"]: item for item in results}

    def _get_user_cart_item(self, user_id: str, item_id: str) -> CartItem:
        """
        Get a cart item ensuring it belongs to the user's cart.

        Args:
            user_id: UUID string of the authenticated user.
            item_id: UUID string of the cart item.

        Returns:
            CartItem instance.

        Raises:
            NotFoundError: If item doesn't exist or doesn't belong to user.
        """
        try:
            cart_item = CartItem.objects.select_related("cart").get(id=item_id)
        except CartItem.DoesNotExist:
            raise NotFoundError("Cart item not found")

        if str(cart_item.cart.user_id) != str(user_id):
            raise NotFoundError("Cart item not found")

        return cart_item
