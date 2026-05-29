"""
RetailRocket Ecommerce Dataset Ingestion Script.

Ingests user interaction events (view, add_to_cart, purchase) from the
RetailRocket dataset for sequence model training.

Usage:
    python -m app.application.ingest_retailrocket

Features:
- Handles missing dataset file gracefully
- Idempotent: skips duplicate interaction records
- Stores as UserInteraction records in the database
- Reports total sequences generated on completion
"""

import asyncio
import csv
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.database import async_session_factory, engine, init_db
from app.infrastructure.db.models import EventType, UserInteraction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

RETAILROCKET_EVENT_MAP = {
    "view": EventType.view,
    "addtocart": EventType.add_to_cart,
    "transaction": EventType.purchase,
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_interaction_record(row: dict) -> dict | None:
    """
    Parse a single RetailRocket interaction record.

    Expected CSV columns: timestamp, visitorid, event, itemid, transactionid

    The RetailRocket dataset uses millisecond timestamps and numeric IDs.
    We map these to UUIDs using a deterministic namespace for consistency.

    Returns:
        Parsed dict with normalized fields, or None if invalid.
    """
    timestamp_ms = row.get("timestamp", "").strip()
    visitor_id = row.get("visitorid", "").strip()
    event = row.get("event", "").strip().lower()
    item_id = row.get("itemid", "").strip()

    if not all([timestamp_ms, visitor_id, event, item_id]):
        return None

    # Map event type
    event_type = RETAILROCKET_EVENT_MAP.get(event)
    if event_type is None:
        return None

    # Convert timestamp (milliseconds since epoch)
    try:
        ts = int(timestamp_ms)
        event_time = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
    except (ValueError, OSError):
        return None

    # Generate deterministic UUIDs from numeric IDs
    namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    user_uuid = uuid.uuid5(namespace, f"user_{visitor_id}")
    product_uuid = uuid.uuid5(namespace, f"item_{item_id}")

    # Unique interaction ID for deduplication
    interaction_id = f"{visitor_id}_{item_id}_{event}_{timestamp_ms}"

    return {
        "interaction_id": interaction_id,
        "user_id": user_uuid,
        "product_id": product_uuid,
        "event_type": event_type,
        "timestamp": event_time,
        "visitor_id": visitor_id,
        "item_id": item_id,
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


async def check_existing_interactions(
    session: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID, event_type: str, timestamp: datetime
) -> bool:
    """Check if an interaction already exists (deduplication)."""
    result = await session.execute(
        select(UserInteraction.id).where(
            UserInteraction.user_id == user_id,
            UserInteraction.product_id == product_id,
            UserInteraction.event_type == event_type,
            UserInteraction.timestamp == timestamp,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def ingest_batch(session: AsyncSession, records: list[dict]) -> int:
    """Insert a batch of interaction records, skipping duplicates. Returns count inserted."""
    if not records:
        return 0

    inserted = 0
    for record in records:
        # Check for duplicate
        exists = await check_existing_interactions(
            session,
            record["user_id"],
            record["product_id"],
            record["event_type"],
            record["timestamp"],
        )
        if exists:
            continue

        interaction = UserInteraction(
            user_id=record["user_id"],
            product_id=record["product_id"],
            event_type=record["event_type"],
            timestamp=record["timestamp"],
        )
        session.add(interaction)
        inserted += 1

    if inserted > 0:
        await session.commit()

    return inserted


def count_sequences(user_interactions: dict[str, list]) -> int:
    """
    Count the number of user interaction sequences.

    A sequence is defined as a series of interactions by a single user,
    ordered by timestamp. Each unique user represents one sequence.
    """
    return len(user_interactions)


async def run_ingestion() -> None:
    """
    Run the RetailRocket ingestion pipeline.

    Steps:
    1. Check dataset file exists
    2. Initialize database
    3. Parse interaction events
    4. Store as UserInteraction records (idempotent)
    5. Report total sequences generated
    """
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("RetailRocket Ingestion - Starting")
    logger.info("=" * 60)

    # Check dataset path
    dataset_path = Path(settings.retailrocket_path)

    # Look for CSV files (events.csv is the main file)
    data_files = []
    if dataset_path.is_dir():
        # Prefer events.csv if it exists
        events_file = dataset_path / "events.csv"
        if events_file.exists():
            data_files = [events_file]
        else:
            data_files = sorted(dataset_path.glob("*.csv"))
    elif dataset_path.is_file():
        data_files = [dataset_path]

    if not data_files:
        logger.error(
            "Dataset not found at: %s. "
            "Please download the RetailRocket dataset and place it in the configured path.",
            settings.retailrocket_path,
        )
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()

    total_ingested = 0
    total_skipped = 0
    total_errors = 0
    batch_size = 500
    user_sequences: dict[str, int] = {}  # Track unique users for sequence count

    async with async_session_factory() as session:
        for data_file in data_files:
            logger.info("Processing file: %s", data_file.name)
            batch: list[dict] = []

            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for line_num, row in enumerate(reader, 1):
                        parsed = parse_interaction_record(row)
                        if parsed:
                            batch.append(parsed)
                            # Track user for sequence counting
                            visitor_id = parsed["visitor_id"]
                            user_sequences[visitor_id] = user_sequences.get(visitor_id, 0) + 1
                        else:
                            total_errors += 1

                        # Process batch
                        if len(batch) >= batch_size:
                            inserted = await ingest_batch(session, batch)
                            total_ingested += inserted
                            total_skipped += len(batch) - inserted
                            batch = []

                            if line_num % 10000 == 0:
                                logger.info(
                                    "Progress: %d lines processed, %d ingested, %d sequences",
                                    line_num,
                                    total_ingested,
                                    len(user_sequences),
                                )

                # Process remaining batch
                if batch:
                    inserted = await ingest_batch(session, batch)
                    total_ingested += inserted
                    total_skipped += len(batch) - inserted

            except Exception as e:
                logger.error("Error processing file %s: %s", data_file.name, str(e))

    # Summary
    total_sequences = len(user_sequences)

    logger.info("=" * 60)
    logger.info("RetailRocket Ingestion - Complete")
    logger.info("=" * 60)
    logger.info("Total interactions ingested: %d", total_ingested)
    logger.info("Total interactions skipped (duplicates): %d", total_skipped)
    logger.info("Total sequences generated (unique users): %d", total_sequences)
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
