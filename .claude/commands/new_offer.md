# Ajout d'un nouveau fournisseur d'énergie

## 🎯 Objectif

Cette commande guide l'ajout d'un nouveau fournisseur d'énergie avec son scraper de prix.

## 📋 Étape 1 : Analyser les PDFs fournis

**IMPORTANT** : Avant toute chose, télécharge et analyse les PDFs pour comprendre leur structure.

```bash
# Utiliser ce script pour analyser un PDF
uv run --env-file /dev/null python << 'EOF'
import asyncio
import httpx
import pdfplumber
import io

async def analyze_pdf(url: str):
    print(f"Downloading {url}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)

    if response.status_code != 200:
        print(f"ERROR: HTTP {response.status_code}")
        return

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages[:2]):  # First 2 pages
            text = page.extract_text() or ""
            print(f"\n=== Page {i+1} ===")
            for j, line in enumerate(text.split('\n')):
                print(f"{j:3d}: {repr(line)}")

# REMPLACER PAR L'URL DU PDF
asyncio.run(analyze_pdf("URL_DU_PDF_ICI"))
EOF
```

Cette analyse permet de :
- Voir la structure ligne par ligne du PDF
- Identifier les patterns de prix (ex: `0,1234` pour les €/kWh)
- Repérer les formats de tableau (BASE vs HC/HP côte à côte ou séparés)
- Trouver la date de validité

---

## 📋 Étape 2 : Identifier les informations

Après analyse du PDF, extraire :

### Informations du fournisseur
- **Nom du fournisseur** : Ex: "Mint Énergie", "Vattenfall"
- **Site web** : URL du site officiel
- **URL(s) source des tarifs** : URLs des PDFs

### Structure des données
- **Format du tableau** : BASE et HC/HP côte à côte ou séparés ?
- **Prix HTT ou TTC** : Généralement TTC pour les particuliers
- **Pattern des prix kWh** : Ex: `0,1234` (4 décimales après virgule)
- **Pattern des abonnements** : Ex: `12,34` (2 décimales)

### Types d'offres
- **BASE** : Tarif unique (prix kWh constant)
- **HC_HP** : Heures Creuses / Heures Pleines
- **TEMPO** : Tarif Tempo (bleu, blanc, rouge)
- **ZEN_FLEX** : Jours Éco/Sobriété (EDF)
- **BASE_WEEKEND** / **HC_WEEKEND** : Tarifs week-end

### Puissances disponibles
- BASE : généralement 3, 6, 9, 12, 15, 18, 24, 30, 36 kVA
- HC/HP : généralement 6, 9, 12, 15, 18, 24, 30, 36 kVA (pas de 3 kVA)

---

## 🔧 Étape 3 : Fichiers à créer/modifier

### 1. Créer le scraper
**Fichier** : `apps/api/src/services/price_scrapers/{provider}_scraper.py`

S'inspirer des scrapers existants :
- `edf_scraper.py` : PDF avec pdfplumber, offres complexes (BASE, HC/HP, TEMPO, ZEN)
- `mint_scraper.py` : PDF avec tableaux côte à côte BASE + HC/HP
- `engie_scraper.py` : HTML avec BeautifulSoup

Structure type :
```python
"""
{Provider} price scraper - Fetches tariffs from official PDFs
"""
import re
from typing import List, Dict
import httpx
import pdfplumber
import io
from datetime import datetime, UTC

from .base import BasePriceScraper, OfferData, run_sync_in_thread


class {Provider}Scraper(BasePriceScraper):
    """Scraper for {Provider} market offers"""

    # URLs par défaut des PDFs
    DEFAULT_URL_1 = "https://..."
    DEFAULT_URL_2 = "https://..."

    # Données de fallback (OBLIGATOIRE - extraites manuellement des PDFs)
    FALLBACK_PRICES = {
        "OFFRE1_BASE": {
            3: {"subscription": 11.73, "kwh": 0.1777},
            6: {"subscription": 15.47, "kwh": 0.1777},
            # ... toutes les puissances
        },
        "OFFRE1_HC_HP": {
            6: {"subscription": 16.01, "hp": 0.1891, "hc": 0.1495},
            # ... toutes les puissances (pas de 3 kVA)
        },
    }

    def __init__(self, scraper_urls: list[str] | None = None):
        super().__init__("{Provider}")
        self.scraper_urls = scraper_urls or [self.DEFAULT_URL_1, self.DEFAULT_URL_2]

    async def fetch_offers(self) -> List[OfferData]:
        """Fetch tariffs from PDFs"""
        # Télécharger chaque PDF
        # Parser avec run_sync_in_thread(self._parse_pdf, content, ...)
        # Retourner fallback si erreur
        pass

    def _parse_pdf(self, pdf_content: bytes, ...) -> List[OfferData]:
        """Parse PDF content - SYNC function for thread pool"""
        # Utiliser pdfplumber
        # Extraire les prix avec regex adaptés à la structure du PDF
        pass

    def _extract_base_prices(self, text: str) -> Dict[int, Dict]:
        """Extract BASE prices from PDF text"""
        pass

    def _extract_hc_hp_prices(self, text: str) -> Dict[int, Dict]:
        """Extract HC/HP prices from PDF text"""
        pass

    def _get_fallback_offers(self) -> List[OfferData]:
        """Generate offers from fallback data"""
        pass

    async def validate_data(self, offers: List[OfferData]) -> bool:
        """Validate extracted data"""
        pass
```

### 2. Enregistrer le scraper
**Fichier** : `apps/api/src/services/price_scrapers/__init__.py`

```python
from .{provider}_scraper import {Provider}Scraper

__all__ = [
    # ... existing ...
    "{Provider}Scraper",
]
```

### 3. Configurer le service
**Fichier** : `apps/api/src/services/price_update_service.py`

```python
# Dans les imports
from .price_scrapers import ..., {Provider}Scraper

# Dans SCRAPERS
"{Provider}": {Provider}Scraper,

# Dans PROVIDER_DEFAULTS
"{Provider}": {"website": "https://www.provider.fr"},
```

### 4. Mettre à jour le frontend
**Fichier** : `apps/web/src/pages/AdminOffers.tsx`

Ajouter dans `urlLabels` (2 endroits - lignes ~880 et ~2430) :
```typescript
'{Provider}': ['Offre 1 (PDF)', 'Offre 2 (PDF)', ...],
```

---

## ✅ Étape 4 : Tester le scraper

```bash
# Test du parsing des PDFs
uv run --env-file /dev/null python << 'EOF'
import asyncio
import httpx
import pdfplumber
import io
import re

# Copier ici les fonctions d'extraction pour tester
def extract_base_prices(text):
    # ...
    pass

def extract_hchp_prices(text):
    # ...
    pass

async def test():
    urls = [
        "URL_PDF_1",
        "URL_PDF_2",
    ]

    for url in urls:
        print(f"\n=== {url.split('/')[-1]} ===")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            text = pdf.pages[0].extract_text() or ""

        base = extract_base_prices(text)
        hchp = extract_hchp_prices(text)

        print(f"BASE: {len(base)} offres")
        for p, d in sorted(base.items()):
            print(f"  {p} kVA: {d}")

        print(f"HC/HP: {len(hchp)} offres")
        for p, d in sorted(hchp.items()):
            print(f"  {p} kVA: {d}")

asyncio.run(test())
EOF
```

---

## 📝 Patterns regex courants

### Prix kWh (4 décimales)
```python
# Format: "0,1234" ou "0.1234"
re.search(r'0[,.](\d{4})', text)
```

### Abonnement (2 décimales)
```python
# Format: "12,34" ou "12.34"
re.search(r'(\d+)[,.](\d{2})', text)
```

### Puissance kVA
```python
# Format: "6 kVA" ou "6kVA"
re.match(r'^\s*(\d+)\s*kVA', line)
```

### Lignes avec BASE et HC/HP côte à côte
```python
# Format: "6 kVA 11,07 15,47 6 kVA 11,30 16,01"
re.search(r'(\d+)\s*kVA\s+[\d,]+\s+[\d,]+\s+(\d+)\s*kVA\s+([\d,]+)\s+([\d,]+)', line)
```

### Date de validité
```python
# Format: "applicable au 01/08/2025"
re.search(r'applicable\s+(?:au|du)\s+(\d{2})/(\d{2})/(\d{4})', text)
```

---

## 📊 Résumé des offres attendues

| Type | Puissances | Champs requis |
|------|------------|---------------|
| BASE | 3-36 kVA (9) | subscription, base_price |
| HC_HP | 6-36 kVA (8) | subscription, hp_price, hc_price |
| TEMPO | 6-36 kVA (8) | subscription, tempo_blue_hc/hp, tempo_white_hc/hp, tempo_red_hc/hp |

---

## ⚠️ Points d'attention

1. **Toujours implémenter FALLBACK_PRICES** : Les PDFs peuvent changer d'URL ou de format
2. **Prix TTC** : Les grilles tarifaires particuliers sont généralement en TTC
3. **run_sync_in_thread** : pdfplumber est synchrone, l'exécuter dans un thread pool
4. **Validation** : Vérifier 0 < prix < 1€/kWh pour les kWh, 0 < abo < 100€ pour abonnements
5. **offer_url** : Définir l'URL source pour chaque offre (traçabilité)
