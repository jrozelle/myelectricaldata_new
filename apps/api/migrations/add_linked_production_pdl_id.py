"""
Migration: Add linked_production_pdl_id column to pdls table

This migration adds a linked_production_pdl_id column to the pdls table
to allow users to link a production PDL to a consumption PDL for combined graphs.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from src.models.database import async_session_maker


async def migrate():
    """Add linked_production_pdl_id column to pdls table"""
    async with async_session_maker() as session:
        async with session.begin():
            # Add linked_production_pdl_id column with foreign key constraint
            await session.execute(text('''
                ALTER TABLE pdls
                ADD COLUMN IF NOT EXISTS linked_production_pdl_id VARCHAR(36)
            '''))

            # Add foreign key constraint
            await session.execute(text('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_pdls_linked_production_pdl_id'
                    ) THEN
                        ALTER TABLE pdls
                        ADD CONSTRAINT fk_pdls_linked_production_pdl_id
                        FOREIGN KEY (linked_production_pdl_id) REFERENCES pdls(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
            '''))

            print("✅ Added linked_production_pdl_id column to pdls table")


async def rollback():
    """Remove linked_production_pdl_id column from pdls table"""
    async with async_session_maker() as session:
        async with session.begin():
            # Drop foreign key constraint first
            await session.execute(text('''
                ALTER TABLE pdls
                DROP CONSTRAINT IF EXISTS fk_pdls_linked_production_pdl_id
            '''))

            # Drop the column
            await session.execute(text('''
                ALTER TABLE pdls
                DROP COLUMN IF EXISTS linked_production_pdl_id
            '''))

            print("✅ Removed linked_production_pdl_id column from pdls table")


if __name__ == "__main__":
    print("Running migration: add_linked_production_pdl_id")
    asyncio.run(migrate())
    print("Migration completed successfully!")
