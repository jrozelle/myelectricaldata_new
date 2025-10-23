"""
Migration script to add contract_end_date column to pdls table.

This column stores the contract end date for each PDL.

Run with: python -m migrations.add_contract_end_date
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.models.database import engine
from src.models.pdl import PDL


async def migrate():
    """Add contract_end_date column to pdls table"""

    async with engine.begin() as conn:
        print("🔍 Checking if column already exists...")

        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pdls'
            AND column_name = 'contract_end_date'
        """))

        exists = result.fetchone() is not None

        if exists:
            print("✅ Column 'contract_end_date' already exists. Skipping migration.")
            return

        print("📝 Adding column 'contract_end_date' to pdls table...")

        await conn.execute(text("""
            ALTER TABLE pdls
            ADD COLUMN contract_end_date DATE NULL
        """))

        print("✅ Migration completed successfully!")
        print("ℹ️  Column 'contract_end_date' has been added to track contract end dates.")


if __name__ == "__main__":
    print("=" * 80)
    print("Migration: Add contract_end_date to PDLs")
    print("=" * 80)

    asyncio.run(migrate())

    print("=" * 80)
    print("✅ All done!")
    print("=" * 80)
