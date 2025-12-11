"""
Migration: Update ALPIQ scraper URLs to use official PDFs

This migration ensures the ALPIQ provider exists and has the correct
scraper URLs pointing to the official PDFs:
- PRIX_STABLE_18.pdf: Électricité Stable -21,5% (prix fixe jusqu'au 30/11/2027)
- gtr_elec_part.pdf: Électricité Stable -8% + Électricité Référence -4%
"""
import asyncio
import uuid
from datetime import datetime, UTC
from sqlalchemy import text, select
from src.models.database import get_db
from src.models import EnergyProvider


async def migrate():
    """Create/update ALPIQ provider with official PDF URLs"""
    async for db in get_db():
        try:
            # Check if ALPIQ provider exists
            result = await db.execute(
                select(EnergyProvider).where(EnergyProvider.name == "ALPIQ")
            )
            provider = result.scalar_one_or_none()

            alpiq_pdf_urls = [
                "https://particuliers.alpiq.fr/grille-tarifaire/particuliers/PRIX_STABLE_18.pdf",
                "https://particuliers.alpiq.fr/grille-tarifaire/particuliers/gtr_elec_part.pdf",
            ]

            if not provider:
                # Create ALPIQ provider
                provider = EnergyProvider(
                    id=str(uuid.uuid4()),
                    name="ALPIQ",
                    website="https://particuliers.alpiq.fr",
                    scraper_urls=alpiq_pdf_urls,
                    is_active=True,
                )
                db.add(provider)
                print("✅ Created ALPIQ provider with PDF URLs")
            else:
                # Update scraper_urls if different
                current_urls = provider.scraper_urls or []
                if current_urls != alpiq_pdf_urls:
                    provider.scraper_urls = alpiq_pdf_urls
                    provider.updated_at = datetime.now(UTC)
                    print(f"✅ Updated ALPIQ scraper_urls from {current_urls} to {alpiq_pdf_urls}")
                else:
                    print("ℹ️  ALPIQ already has correct scraper_urls")

            await db.commit()
            print("\n✅ Migration completed successfully")
            print("   ALPIQ scraper URLs:")
            for url in alpiq_pdf_urls:
                print(f"   - {url}")
            print("\nNext step: Run the price refresh for ALPIQ:")
            print("  POST /api/admin/offers/refresh/ALPIQ")

        except Exception as e:
            await db.rollback()
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            break


if __name__ == "__main__":
    asyncio.run(migrate())
