"""
UCI Online Retail Dataset Ingestion Script.

Ingests the UCI Online Retail dataset for customer segmentation (RFM analysis).
Parses transaction records and computes per-customer RFM features.

Usage:
    python -m app.application.ingest_uci_retail

Features:
- Handles missing dataset file gracefully
- Idempotent: skips customers already processed in the current run
- Reports total customer records processed on completion
"""

import asyncio
import csv
import logging
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.database import async_session_factory, engine, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database table for RFM training data
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rfm_training_data (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(255) UNIQUE NOT NULL,
    recency_days INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    monetary NUMERIC(12, 2) NOT NULL,
    first_purchase_date TIMESTAMP WITH TIME ZONE,
    last_purchase_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_rfm_training_customer_id ON rfm_training_data(customer_id);
"""


async def ensure_table_exists() -> None:
    """Create the rfm_training_data table if it doesn't exist."""
    async with engine.begin() as conn:
        for statement in CREATE_TABLE_SQL.strip().split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_transaction_record(row: dict) -> dict | None:
    """
    Parse a single UCI Online Retail transaction record.

    Expected CSV columns: InvoiceNo, StockCode, Description, Quantity,
                          InvoiceDate, UnitPrice, CustomerID, Country

    Returns:
        Parsed dict with normalized fields, or None if invalid.
    """
    customer_id = row.get("CustomerID", "").strip()
    if not customer_id:
        return None

    try:
        quantity = int(row.get("Quantity", "0"))
        unit_price = float(row.get("UnitPrice", "0"))
    except (ValueError, TypeError):
        return None

    # Skip cancelled orders (negative quantity) and zero-price items
    if quantity <= 0 or unit_price <= 0:
        return None

    invoice_date_str = row.get("InvoiceDate", "").strip()
    invoice_date = None
    if invoice_date_str:
        for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                invoice_date = datetime.strptime(invoice_date_str, fmt)
                break
            except ValueError:
                continue

    total_amount = quantity * unit_price

    return {
        "customer_id": customer_id,
        "invoice_date": invoice_date,
        "total_amount": total_amount,
    }


def compute_rfm_features(transactions: list[dict], reference_date: datetime) -> dict:
    """
    Compute RFM features from a list of customer transactions.

    Args:
        transactions: List of transaction dicts with invoice_date and total_amount.
        reference_date: Date to compute recency from.

    Returns:
        Dict with recency_days, frequency, monetary, first/last purchase dates.
    """
    dates = [t["invoice_date"] for t in transactions if t["invoice_date"]]
    amounts = [t["total_amount"] for t in transactions]

    if not dates:
        return None

    last_purchase = max(dates)
    first_purchase = min(dates)
    recency_days = (reference_date - last_purchase).days
    frequency = len(transactions)
    monetary = sum(amounts)

    return {
        "recency_days": max(0, recency_days),
        "frequency": frequency,
        "monetary": round(monetary, 2),
        "first_purchase_date": first_purchase,
        "last_purchase_date": last_purchase,
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


async def check_existing_customers(session: AsyncSession, customer_ids: list[str]) -> set[str]:
    """Check which customer_ids already exist in the database."""
    if not customer_ids:
        return set()
    result = await session.execute(
        text("SELECT customer_id FROM rfm_training_data WHERE customer_id = ANY(:ids)"),
        {"ids": customer_ids},
    )
    return {row[0] for row in result.fetchall()}


async def ingest_customers(session: AsyncSession, customer_rfm: dict[str, dict]) -> int:
    """Insert customer RFM records, skipping duplicates. Returns count inserted."""
    if not customer_rfm:
        return 0

    customer_ids = list(customer_rfm.keys())
    existing = await check_existing_customers(session, customer_ids)

    inserted = 0
    for customer_id, rfm in customer_rfm.items():
        if customer_id in existing:
            continue

        await session.execute(
            text(
                "INSERT INTO rfm_training_data "
                "(customer_id, recency_days, frequency, monetary, first_purchase_date, last_purchase_date) "
                "VALUES (:customer_id, :recency_days, :frequency, :monetary, :first_purchase_date, :last_purchase_date) "
                "ON CONFLICT (customer_id) DO NOTHING"
            ),
            {
                "customer_id": customer_id,
                "recency_days": rfm["recency_days"],
                "frequency": rfm["frequency"],
                "monetary": rfm["monetary"],
                "first_purchase_date": rfm["first_purchase_date"],
                "last_purchase_date": rfm["last_purchase_date"],
            },
        )
        inserted += 1

    await session.commit()
    return inserted


async def run_ingestion() -> None:
    """
    Run the UCI Online Retail ingestion pipeline.

    Steps:
    1. Check dataset file exists
    2. Initialize database table
    3. Parse all transactions, group by customer
    4. Compute RFM features per customer
    5. Store in database (idempotent)
    6. Report totals
    """
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("UCI Online Retail Ingestion - Starting")
    logger.info("=" * 60)

    # Check dataset path
    dataset_path = Path(settings.uci_retail_path)

    # Look for CSV files
    data_files = []
    if dataset_path.is_dir():
        data_files = sorted(dataset_path.glob("*.csv")) + sorted(dataset_path.glob("*.xlsx"))
    elif dataset_path.is_file():
        data_files = [dataset_path]

    if not data_files:
        logger.error(
            "Dataset not found at: %s. "
            "Please download the UCI Online Retail dataset and place it in the configured path.",
            settings.uci_retail_path,
        )
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    await ensure_table_exists()

    # Parse all transactions grouped by customer
    customer_transactions: dict[str, list[dict]] = {}
    total_transactions = 0
    total_errors = 0

    for data_file in data_files:
        if data_file.suffix == ".xlsx":
            logger.warning("XLSX files require openpyxl. Skipping: %s", data_file.name)
            continue

        logger.info("Processing file: %s", data_file.name)

        try:
            with open(data_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    parsed = parse_transaction_record(row)
                    if parsed:
                        cid = parsed["customer_id"]
                        if cid not in customer_transactions:
                            customer_transactions[cid] = []
                        customer_transactions[cid].append(parsed)
                        total_transactions += 1
                    else:
                        total_errors += 1
        except Exception as e:
            logger.error("Error processing file %s: %s", data_file.name, str(e))

    logger.info(
        "Parsed %d transactions for %d customers (%d errors)",
        total_transactions,
        len(customer_transactions),
        total_errors,
    )

    # Compute RFM features
    reference_date = datetime.now()
    customer_rfm: dict[str, dict] = {}

    for customer_id, transactions in customer_transactions.items():
        rfm = compute_rfm_features(transactions, reference_date)
        if rfm:
            customer_rfm[customer_id] = rfm

    logger.info("Computed RFM features for %d customers", len(customer_rfm))

    # Store in database
    async with async_session_factory() as session:
        total_ingested = await ingest_customers(session, customer_rfm)
        total_skipped = len(customer_rfm) - total_ingested

    # Summary
    logger.info("=" * 60)
    logger.info("UCI Online Retail Ingestion - Complete")
    logger.info("=" * 60)
    logger.info("Total customer records processed: %d", len(customer_rfm))
    logger.info("Total records ingested: %d", total_ingested)
    logger.info("Total records skipped (duplicates): %d", total_skipped)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running the ingestion pipeline."""
    asyncio.run(run_ingestion())


if __name__ == "__main__":
    main()
