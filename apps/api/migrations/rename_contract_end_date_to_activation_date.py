"""
Migration script to rename contract_end_date column to activation_date in pdls table.

This column stores the contract activation date from Enedis API (last_activation_date field).

Run with: python migrations/rename_contract_end_date_to_activation_date.py
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
    """Rename contract_end_date column to activation_date in pdls table"""

    async with engine.begin() as conn:
        print("🔍 Checking if contract_end_date column exists...")

        # Check if old column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pdls'
            AND column_name = 'contract_end_date'
        """))

        old_exists = result.fetchone() is not None

        # Check if new column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pdls'
            AND column_name = 'activation_date'
        """))

        new_exists = result.fetchone() is not None

        if new_exists:
            print("✅ Column 'activation_date' already exists.")
            if old_exists:
                print("📝 Dropping old 'contract_end_date' column...")
                await conn.execute(text("ALTER TABLE pdls DROP COLUMN contract_end_date"))
                print("✅ Old column removed.")
            else:
                print("✅ Migration already complete. Skipping.")
            return

        if old_exists:
            print("📝 Renaming column 'contract_end_date' to 'activation_date'...")
            await conn.execute(text("""
                ALTER TABLE pdls
                RENAME COLUMN contract_end_date TO activation_date
            """))
            print("✅ Migration completed successfully!")
        else:
            print("📝 Adding column 'activation_date' to pdls table...")
            await conn.execute(text("""
                ALTER TABLE pdls
                ADD COLUMN activation_date DATE NULL
            """))
            print("✅ Migration completed successfully!")

        print("ℹ️  Column 'activation_date' will store contract activation date from Enedis API.")


if __name__ == "__main__":
    print("=" * 80)
    print("Migration: Rename contract_end_date to activation_date")
    print("=" * 80)

    asyncio.run(migrate())

    print("=" * 80)
    print("✅ All done!")
    print("=" * 80)
