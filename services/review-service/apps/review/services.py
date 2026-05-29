"""
Business logic for Review Service.

Handles review creation with purchase verification and sentiment analysis.
"""

import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Avg, Count

from apps.core.exceptions import ConflictError, ForbiddenError, ServiceUnavailableError
from apps.core.http_client import ServiceClient
from apps.review.models import Review

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Service layer for review operations.

    Coordinates purchase verification (Order Service),
    sentiment analysis (AI Service), and catalog rating updates
    (Catalog Service) during review creation.
    """

    def __init__(self, authorization_header: str | None = None):
        self.authorization_header = authorization_header
        self.order_client = ServiceClient(settings.ORDER_SERVICE_URL)
        self.ai_client = ServiceClient(settings.AI_SERVICE_URL, timeout_seconds=5.0)
        self.catalog_client = ServiceClient(settings.CATALOG_SERVICE_URL, timeout_seconds=5.0)

    def create_review(self, user_id: str, product_id: str, rating: int, comment: str) -> Review:
        """
        Create a new review after verifying purchase and analyzing sentiment.

        Steps:
        1. Verify the user has a completed order containing the product.
        2. Call AI Service for sentiment analysis.
        3. Store the review with sentiment data (or mark pending if AI unavailable).

        Args:
            user_id: UUID of the reviewing user.
            product_id: UUID of the product being reviewed.
            rating: Integer rating 1-5.
            comment: Review text (1-2000 chars).

        Returns:
            Created Review instance.

        Raises:
            ForbiddenError: If user hasn't purchased the product.
            ConflictError: If user already reviewed this product.
        """
        # Step 1: Verify purchase
        self._verify_purchase(user_id, product_id)

        # Step 2: Analyze sentiment
        sentiment_label, sentiment_score, sentiment_status = self._analyze_sentiment(comment)

        # Step 3: Store review
        try:
            review = Review.objects.create(
                user_id=user_id,
                product_id=product_id,
                rating=rating,
                comment=comment,
                sentiment_label=sentiment_label,
                sentiment_score=sentiment_score,
                sentiment_status=sentiment_status,
            )
        except IntegrityError:
            raise ConflictError("You have already reviewed this product")

        # Step 4: Update catalog product rating
        self._update_catalog_rating(product_id)

        return review

    def get_reviews_for_product(self, product_id: str, page: int = 1, page_size: int = 10):
        """
        Get paginated reviews for a product, sorted newest first.

        Args:
            product_id: UUID of the product.
            page: Page number (1-indexed).
            page_size: Number of reviews per page (max 50).

        Returns:
            Tuple of (queryset, aggregation_data) for the view to paginate.
        """
        queryset = Review.objects.filter(product_id=product_id).order_by("-created_at")
        return queryset

    def get_product_review_stats(self, product_id: str) -> dict:
        """
        Calculate average rating and total review count for a product.

        Returns:
            Dict with 'average_rating' (1 decimal, or 0.0) and 'total_reviews'.
        """
        stats = Review.objects.filter(product_id=product_id).aggregate(
            average_rating=Avg("rating"),
            total_reviews=Count("id"),
        )
        average_rating = stats["average_rating"]
        if average_rating is not None:
            average_rating = round(average_rating, 1)
        else:
            average_rating = 0.0

        return {
            "average_rating": average_rating,
            "total_reviews": stats["total_reviews"],
        }

    def _verify_purchase(self, user_id: str, product_id: str):
        """
        Verify the user has a completed order containing the product.

        Calls Order Service to get user's orders and checks if any completed
        order contains the specified product.

        Raises:
            ForbiddenError: If no completed order with the product is found.
        """
        headers = {}
        if self.authorization_header:
            headers["Authorization"] = self.authorization_header

        try:
            # Get user's orders from Order Service
            response = self.order_client.get(
                "/api/v1/orders/",
                headers=headers,
                params={"page_size": 100},
            )
        except ServiceUnavailableError:
            logger.warning(
                "Order Service unavailable during purchase verification for user %s",
                user_id,
            )
            raise ForbiddenError(
                "Unable to verify purchase. Please try again later."
            )

        # Check if any completed order contains the product
        orders = response.get("data", [])
        has_purchased = False

        for order in orders:
            if order.get("status") == "completed":
                # Need to check order detail for items
                order_id = order.get("id")
                try:
                    detail_response = self.order_client.get(
                        f"/api/v1/orders/{order_id}",
                        headers=headers,
                    )
                    order_detail = detail_response.get("data", {})
                    items = order_detail.get("items", [])
                    for item in items:
                        if str(item.get("product_id")) == str(product_id):
                            has_purchased = True
                            break
                except (ServiceUnavailableError, Exception):
                    logger.warning(
                        "Failed to fetch order detail %s for purchase verification",
                        order_id,
                    )
                    continue

            if has_purchased:
                break

        if not has_purchased:
            raise ForbiddenError(
                "You can only review products you have purchased"
            )

    def _analyze_sentiment(self, text: str) -> tuple:
        """
        Call AI Service for sentiment analysis.

        Returns:
            Tuple of (sentiment_label, sentiment_score, sentiment_status).
            If AI is unavailable, returns (None, None, "pending").
        """
        try:
            response = self.ai_client.post(
                "/api/v1/sentiment",
                json={"text": text},
            )
            data = response.get("data", {})
            label = data.get("label")
            confidence = data.get("confidence")
            return label, confidence, "completed"
        except (ServiceUnavailableError, Exception) as e:
            logger.warning("AI Service unavailable for sentiment analysis: %s", str(e))
            return None, None, "pending"

    def _update_catalog_rating(self, product_id: str) -> None:
        """
        Update the product's rating_avg and rating_count in the Catalog Service.

        Computes the current average rating and total review count for the product,
        then calls PATCH /api/v1/products/{product_id} on the Catalog Service.

        This is a best-effort operation — failures are logged but do not
        prevent the review from being created.

        Args:
            product_id: UUID of the product to update ratings for.
        """
        try:
            stats = self.get_product_review_stats(product_id)
            average_rating = stats["average_rating"]
            total_reviews = stats["total_reviews"]

            headers = {}
            if self.authorization_header:
                headers["Authorization"] = self.authorization_header

            self.catalog_client.patch(
                f"/api/v1/products/{product_id}/",
                headers=headers,
                json={
                    "rating_avg": average_rating,
                    "rating_count": total_reviews,
                },
            )
            logger.info(
                "Updated catalog rating for product %s: avg=%.1f, count=%d",
                product_id,
                average_rating,
                total_reviews,
            )
        except (ServiceUnavailableError, Exception) as e:
            logger.warning(
                "Failed to update catalog rating for product %s: %s",
                product_id,
                str(e),
            )
