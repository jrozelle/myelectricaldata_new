"""
Migration script to add oldest_available_data_date column to pdls table.

This column stores the oldest date where Enedis has data available for this PDL,
corresponding to the meter's activation date. This prevents unnecessary API calls
for dates before the meter was activated.

Run with: python -m migrations.add_oldest_available_data_date
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.config.database import engine, async_session
from src.models.pdl import PDL


async def migrate():
    """Add oldest_available_data_date column to pdls table"""

    async with engine.begin() as conn:
        print("🔍 Checking if column already exists...")

        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pdls'
            AND column_name = 'oldest_available_data_date'
        """))

        exists = result.fetchone() is not None

        if exists:
            print("✅ Column 'oldest_available_data_date' already exists. Skipping migration.")
            return

        print("📝 Adding column 'oldest_available_data_date' to pdls table...")

        await conn.execute(text("""
            ALTER TABLE pdls
            ADD COLUMN oldest_available_data_date DATE NULL
        """))

        print("✅ Migration completed successfully!")
        print("ℹ️  Column 'oldest_available_data_date' has been added to track meter activation dates.")


if __name__ == "__main__":
    print("=" * 80)
    print("Migration: Add oldest_available_data_date to PDLs")
    print("=" * 80)

    asyncio.run(migrate())

    print("=" * 80)
    print("✅ All done!")
    print("=" * 80)
