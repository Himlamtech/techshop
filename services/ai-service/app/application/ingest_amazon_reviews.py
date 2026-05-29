"""
Amazon Reviews Dataset Ingestion Script.

Ingests Amazon product reviews for sentiment model training.
Parses review records from JSON Lines files and stores them in the database.

Usage:
    python -m app.application.ingest_amazon_reviews

Features:
- Handles missing dataset file gracefully
- Idempotent: skips duplicate records based on review_id
- Reports total records ingested on completion
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.database import async_session_factory, engine, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database table for sentiment training data
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sentiment_training_data (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(255) UNIQUE NOT NULL,
    product_id VARCHAR(255),
    reviewer_id VARCHAR(255),
    rating SMALLINT NOT NULL,
    review_text TEXT NOT NULL,
    summary TEXT,
    sentiment_label VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sentiment_training_review_id ON sentiment_training_data(review_id);
CREATE INDEX IF NOT EXISTS ix_sentiment_training_sentiment ON sentiment_training_data(sentiment_label);
"""


async def ensure_table_exists() -> None:
    """Create the sentiment_training_data table if it doesn't exist."""
    async with engine.begin() as conn:
        for statement in CREATE_TABLE_SQL.strip().split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def derive_sentiment_label(rating: int) -> str:
    """
    Derive sentiment label from star rating.

    1-2 stars → negative
    3 stars → neutral
    4-5 stars → positive
    """
    if rating <= 2:
        return "negative"
    elif rating == 3:
        return "neutral"
    else:
        return "positive"


def parse_review_record(record: dict) -> dict | None:
    """
    Parse a single Amazon review record.

    Expected fields: reviewerID, asin, overall, reviewText, summary.

    Returns:
        Parsed dict with normalized fields, or None if invalid.
    """
    rating = record.get("overall")
    review_text = record.get("reviewText", "")

    if not rating or not review_text:
        return None

    rating = int(rating)
    reviewer_id = record.get("reviewerID", "")
    product_id = record.get("asin", "")
    summary = record.get("summary", "")

    # Generate a unique review_id from reviewer + product + timestamp
    unix_time = record.get("unixReviewTime", "")
    review_id = f"{reviewer_id}_{product_id}_{unix_time}"

    return {
        "review_id": review_id,
        "product_id": product_id,
        "reviewer_id": reviewer_id,
        "rating": rating,
        "review_text": review_text.strip(),
        "summary": summary.strip() if summary else None,
        "sentiment_label": derive_sentiment_label(rating),
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


async def check_existing_ids(session: AsyncSession, review_ids: list[str]) -> set[str]:
    """Check which review_ids already exist in the database."""
    if not review_ids:
        return set()
    result = await session.execute(
        text("SELECT review_id FROM sentiment_training_data WHERE review_id = ANY(:ids)"),
        {"ids": review_ids},
    )
    return {row[0] for row in result.fetchall()}


async def ingest_batch(session: AsyncSession, records: list[dict]) -> int:
    """Insert a batch of records, skipping duplicates. Returns count inserted."""
    if not records:
        return 0

    review_ids = [r["review_id"] for r in records]
    existing = await check_existing_ids(session, review_ids)

    new_records = [r for r in records if r["review_id"] not in existing]
    if not new_records:
        return 0

    # Bulk insert using raw SQL for performance
    for record in new_records:
        await session.execute(
            text(
                "INSERT INTO sentiment_training_data "
                "(review_id, product_id, reviewer_id, rating, review_text, summary, sentiment_label) "
                "VALUES (:review_id, :product_id, :reviewer_id, :rating, :review_text, :summary, :sentiment_label) "
                "ON CONFLICT (review_id) DO NOTHING"
            ),
            record,
        )

    await session.commit()
    return len(new_records)


async def run_ingestion() -> None:
    """
    Run the Amazon Reviews ingestion pipeline.

    Steps:
    1. Check dataset file exists
    2. Initialize database table
    3. Parse records in batches
    4. Insert with duplicate detection
    5. Report totals
    """
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("Amazon Reviews Ingestion - Starting")
    logger.info("=" * 60)

    # Check dataset path
    dataset_path = Path(settings.amazon_reviews_path)

    # Look for JSON Lines files in the dataset directory
    data_files = []
    if dataset_path.is_dir():
        data_files = sorted(dataset_path.glob("*.jsonl")) + sorted(dataset_path.glob("*.json"))
    elif dataset_path.is_file():
        data_files = [dataset_path]

    if not data_files:
        logger.error(
            "Dataset not found at: %s. "
            "Please download the Amazon Reviews dataset and place it in the configured path.",
            settings.amazon_reviews_path,
        )
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    await ensure_table_exists()

    total_ingested = 0
    total_skipped = 0
    total_errors = 0
    batch_size = 500

    async with async_session_factory() as session:
        for data_file in data_files:
            logger.info("Processing file: %s", data_file.name)
            batch: list[dict] = []

            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            record = json.loads(line)
                            parsed = parse_review_record(record)
                            if parsed:
                                batch.append(parsed)
                            else:
                                total_errors += 1
                        except json.JSONDecodeError:
                            total_errors += 1
                            continue

                        # Process batch
                        if len(batch) >= batch_size:
                            inserted = await ingest_batch(session, batch)
                            total_ingested += inserted
                            total_skipped += len(batch) - inserted
                            batch = []

                            if line_num % 5000 == 0:
                                logger.info(
                                    "Progress: %d lines processed, %d ingested",
                                    line_num,
                                    total_ingested,
                                )

                # Process remaining batch
                if batch:
                    inserted = await ingest_batch(session, batch)
                    total_ingested += inserted
                    total_skipped += len(batch) - inserted

            except Exception as e:
                logger.error("Error processing file %s: %s", data_file.name, str(e))

    # Summary
    logger.info("=" * 60)
    logger.info("Amazon Reviews Ingestion - Complete")
    logger.info("=" * 60)
    logger.info("Total records ingested: %d", total_ingested)
    logger.info("Total records skipped (duplicates): %d", total_skipped)
    logger.info("Total records with errors: %d", total_errors)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running the ingestion pipeline."""
    asyncio.run(run_ingestion())


if __name__ == "__main__":
    main()
