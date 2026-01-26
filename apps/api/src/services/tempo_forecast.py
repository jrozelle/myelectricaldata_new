"""
Service de prévision Tempo basé sur l'algorithme RTE officiel

L'algorithme RTE utilise la consommation nette normalisée comparée à deux seuils :
- Seuil_Blanc+Rouge = A - B.JourTempo - C.StockRestant(Blanc+Rouge)
- Seuil_Rouge = A' - B'.JourTempo - C'.StockRestant(Rouge)

Où :
- Consommation nette = Consommation nationale - (Production solaire + Production éolienne)
- Consommation nette normalisée = (Consommation nette - 46050) / 2160

Paramètres calibrés (source RTE) :
- Blanc+Rouge : A=4, B=0.015, C=0.026
- Rouge : A'=3.15, B'=0.01, C'=0.031

Référence : Documentation RTE - Création de l'algorithme Tempo
https://www.services-rte.com/files/live/sites/services-rte/files/pdf/20160106_Methode_de_choix_des_jours_Tempo.pdf
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Paramètres calibrés par RTE (source: documentation officielle)
PARAMS_BLANC_ROUGE = {"A": 4.0, "B": 0.015, "C": 0.026}
PARAMS_ROUGE = {"A": 3.15, "B": 0.01, "C": 0.031}

# Paramètres de normalisation calibrés pour 2025-2026
#
# Les valeurs RTE 2016 (46050/2160 MW) ne sont plus adaptées car la consommation
# française a évolué. En janvier 2026, la consommation nette moyenne est ~55-70 GW.
#
# Calibration actuelle (basée sur comparaison avec Selectra janvier 2026) :
# - Consommation nette moyenne : 55 000 - 70 000 MW
# - Seuils RTE typiques en janvier : ~0.9 (blanc+rouge) et ~1.3 (rouge)
#
# Formule : normalized = (conso_nette - OFFSET) / SCALE
# Avec offset=55000 et scale=8000 :
# - 59 000 MW → norm=0.5 (BLEU)
# - 62 500 MW → norm=0.94 (seuil BLANC)
# - 65 000 MW → norm=1.25 (BLANC/ROUGE)
# - 67 500 MW → norm=1.56 (ROUGE)
NORMALIZATION_OFFSET = 55000  # MW (calibré pour Selectra 01/2026)
NORMALIZATION_SCALE = 8000  # MW (calibré pour Selectra 01/2026)

# Paramètres de correction de température (source: document RTE 2016)
# γ est la sensibilité de la consommation à la température
# κ est la moyenne du quantile 30% de la température moyenne journalière
GAMMA = -0.1176  # Coefficient de correction température
KAPPA = 8.3042  # Température moyenne quantile 30% (°C)

# Quotas annuels Tempo
QUOTA_BLEU = 300
QUOTA_BLANC = 43
QUOTA_ROUGE = 22
TOTAL_DAYS = 365


@dataclass
class ConsumptionForecast:
    """Prévision de consommation pour un jour"""

    date: str  # YYYY-MM-DD
    consumption_mw: float  # Consommation nationale prévue (MW)
    solar_mw: float  # Production solaire prévue (MW)
    wind_mw: float  # Production éolienne prévue (MW)
    net_consumption: float  # Consommation nette (MW)
    normalized_consumption: float  # Consommation nette normalisée
    forecast_type: str  # Type de prévision (D-1, D-2, WEEKLY, ESTIMATED)


@dataclass
class TempoDayForecast:
    """Prévision Tempo pour un jour"""

    date: str  # YYYY-MM-DD
    day_in_season: int  # Jour dans la saison Tempo (1-365)
    probability_blue: float  # Probabilité jour bleu (0-100)
    probability_white: float  # Probabilité jour blanc (0-100)
    probability_red: float  # Probabilité jour rouge (0-100)
    most_likely: str  # Couleur la plus probable (BLUE, WHITE, RED)
    confidence: str  # Niveau de confiance (high, medium, low)
    threshold_white_red: float  # Seuil blanc+rouge calculé
    threshold_red: float  # Seuil rouge calculé
    normalized_consumption: float | None  # Consommation nette normalisée (si disponible)
    forecast_type: str  # Type de données (RTE_FORECAST, HISTORICAL, ESTIMATED)
    factors: dict  # Facteurs explicatifs


class TempoForecastService:
    """Service de prévision Tempo utilisant les APIs RTE"""

    def __init__(self) -> None:
        self.base_url = settings.RTE_BASE_URL
        self.client_id = settings.RTE_CLIENT_ID
        self.client_secret = settings.RTE_CLIENT_SECRET
        self.token_url = f"{self.base_url}/token/oauth/"
        # API Consumption v1 - Prévisions de consommation
        self.consumption_url = f"{self.base_url}/open_api/consumption/v1/short_term"
        self.weekly_forecast_url = f"{self.base_url}/open_api/consumption/v1/weekly_forecasts"
        # API Generation Forecast v3 - Prévisions de production
        self.generation_forecast_url = f"{self.base_url}/open_api/generation_forecast/v3/forecasts"
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _get_access_token(self) -> str:
        """Obtenir un token OAuth2 pour les APIs RTE"""
        from datetime import UTC

        if self._access_token and self._token_expires_at:
            if datetime.now(UTC) < self._token_expires_at:
                return self._access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

            return self._access_token

    async def fetch_consumption_forecast(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """
        Récupérer les prévisions de consommation depuis l'API RTE Consumption

        L'API short_term supporte :
        - D-1 : prévision pour J+1 (demain)
        - D-2 : prévision pour J+2 (après-demain)

        Args:
            start_date: Date de début (utilisé pour déterminer les jours à récupérer)
            end_date: Date de fin

        Returns:
            Liste des prévisions de consommation (D-1 et D-2)
        """
        token = await self._get_access_token()
        paris_tz = ZoneInfo("Europe/Paris")
        from datetime import time

        results: list[dict[str, Any]] = []

        # Récupérer D-1 (J+1) et D-2 (J+2)
        forecast_configs = [
            ("D-1", date.today() + timedelta(days=1)),
            ("D-2", date.today() + timedelta(days=2)),
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for forecast_type, target_date in forecast_configs:
                next_day = target_date + timedelta(days=1)
                start_dt = datetime.combine(target_date, time(0, 0, 0)).replace(tzinfo=paris_tz)
                end_dt = datetime.combine(next_day, time(0, 0, 0)).replace(tzinfo=paris_tz)

                logger.info(f"[RTE] Fetching consumption forecast {forecast_type} for {target_date}")

                try:
                    response = await client.get(
                        self.consumption_url,
                        params={
                            "type": forecast_type,
                            "start_date": start_dt.isoformat(),
                            "end_date": end_dt.isoformat(),
                        },
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        entries = data.get("short_term", [])
                        logger.info(
                            f"[RTE] Consumption forecast {forecast_type} received: {len(entries)} entries"
                        )
                        results.extend(entries)
                    else:
                        logger.warning(
                            f"[RTE] Consumption API {forecast_type} error: {response.status_code}"
                        )
                except Exception as e:
                    logger.warning(f"[RTE] Error fetching consumption {forecast_type}: {e}")

        return results

    async def fetch_weekly_forecast(self) -> list[dict[str, Any]]:
        """
        Récupérer les prévisions hebdomadaires (J+3 à J+9) depuis l'API RTE

        Returns:
            Liste des prévisions hebdomadaires
        """
        token = await self._get_access_token()

        logger.info("[RTE] Fetching weekly consumption forecast")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.weekly_forecast_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                logger.warning(f"[RTE] Weekly forecast API error: {response.status_code} - {response.text}")
                return []

            data = response.json()
            return data.get("weekly_forecasts", [])

    async def fetch_generation_forecast(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """
        Récupérer les prévisions de production (solaire, éolien) depuis l'API RTE Generation Forecast v2

        L'API fournit des prévisions D-3, D-2, D-1 et intraday en MW.

        Args:
            start_date: Date de début
            end_date: Date de fin

        Returns:
            Liste des prévisions de production
        """
        token = await self._get_access_token()
        paris_tz = ZoneInfo("Europe/Paris")

        # API v3 Generation Forecast : seul D-1 est disponible
        # L'API RTE ne fournit les prévisions de production (solaire, éolien)
        # que pour J+1 (demain) avec le type D-1.
        # Les types D-2 et D-3 retournent systématiquement 400 Bad Request.
        from datetime import time

        logger.info(f"[RTE] Fetching generation forecast from {start_date} to {end_date}")

        results: list[dict[str, Any]] = []

        # Production types à récupérer
        prod_types = ["SOLAR", "WIND_ONSHORE", "WIND_OFFSHORE"]

        # Seul J+1 (D-1) est disponible pour les prévisions de production
        tomorrow = date.today() + timedelta(days=1)

        # Vérifier si J+1 est dans la plage demandée
        if start_date <= tomorrow <= end_date:
            current_date = tomorrow
            forecast_type = "D-1"
            start_dt = datetime.combine(current_date, time(0, 0, 0)).replace(tzinfo=paris_tz)
            end_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0, 0)).replace(tzinfo=paris_tz)

            for prod_type in prod_types:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            self.generation_forecast_url,
                            params={
                                "start_date": start_dt.isoformat(),
                                "end_date": end_dt.isoformat(),
                                "production_type": prod_type,
                                "type": forecast_type,
                            },
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/json",
                            },
                            timeout=30.0,
                        )

                        if response.status_code == 200:
                            data = response.json()
                            forecasts = data.get("forecasts", [])
                            for forecast in forecasts:
                                forecast["production_type"] = prod_type
                                results.append(forecast)
                        elif response.status_code != 400:
                            # Log uniquement les erreurs autres que 400 (données non disponibles)
                            logger.warning(
                                f"[RTE] Generation forecast error for {prod_type} ({forecast_type}): "
                                f"{response.status_code}"
                            )
                except Exception as e:
                    logger.warning(f"[RTE] Error fetching {prod_type} ({forecast_type}): {e}")

        logger.info(f"[RTE] Generation forecast: received {len(results)} total forecast(s)")

        return results

    def get_season_start(self, target_date: date) -> date:
        """Retourne la date de début de la saison Tempo pour une date donnée"""
        if target_date.month >= 9:
            return date(target_date.year, 9, 1)
        else:
            return date(target_date.year - 1, 9, 1)

    def get_day_in_season(self, target_date: date) -> int:
        """Calcule le numéro du jour dans la saison Tempo (1 = 1er septembre)"""
        season_start = self.get_season_start(target_date)
        return (target_date - season_start).days + 1

    def calculate_thresholds(
        self, day_in_season: int, white_remaining: int, red_remaining: int
    ) -> tuple[float, float]:
        """
        Calcule les seuils selon les formules RTE officielles

        Args:
            day_in_season: Numéro du jour dans la saison (1-365)
            white_remaining: Jours blancs restants
            red_remaining: Jours rouges restants

        Returns:
            Tuple (seuil_blanc_rouge, seuil_rouge)
        """
        blanc_rouge_remaining = white_remaining + red_remaining

        # Formule RTE : Seuil = A - B.JourTempo - C.StockRestant
        seuil_blanc_rouge = (
            PARAMS_BLANC_ROUGE["A"]
            - PARAMS_BLANC_ROUGE["B"] * day_in_season
            - PARAMS_BLANC_ROUGE["C"] * blanc_rouge_remaining
        )

        seuil_rouge = (
            PARAMS_ROUGE["A"]
            - PARAMS_ROUGE["B"] * day_in_season
            - PARAMS_ROUGE["C"] * red_remaining
        )

        return seuil_blanc_rouge, seuil_rouge

    def normalize_consumption(self, net_consumption_mw: float) -> float:
        """
        Normalise la consommation nette selon la formule RTE

        Args:
            net_consumption_mw: Consommation nette en MW

        Returns:
            Consommation nette normalisée (sans unité)
        """
        return (net_consumption_mw - NORMALIZATION_OFFSET) / NORMALIZATION_SCALE

    def is_in_red_calendar(self, target_date: date) -> bool:
        """
        Vérifie si la date est dans le calendrier rouge (1er nov - 31 mars)
        Les jours rouges ne peuvent être tirés que du 1er novembre au 31 mars.
        """
        return target_date.month in [11, 12, 1, 2, 3]

    def is_in_white_calendar(self, target_date: date, is_weekend: bool) -> bool:
        """
        Vérifie si la date est dans le calendrier blanc.
        Les jours blancs peuvent être tirés toute l'année, sauf le dimanche.
        """
        # Dimanche = weekday() == 6
        return target_date.weekday() != 6

    def calculate_probabilities(
        self,
        normalized_consumption: float | None,
        threshold_white_red: float,
        threshold_red: float,
        day_in_season: int,
        is_winter: bool,
        is_weekend: bool,
        blue_remaining: int,
        white_remaining: int,
        red_remaining: int,
        is_sunday: bool = False,
    ) -> tuple[float, float, float]:
        """
        Calcule les probabilités de chaque couleur selon l'algorithme RTE officiel.

        Référence : Document RTE "Méthode de choix des jours Tempo" (page 5)

        L'algorithme RTE compare la consommation nette normalisée à deux seuils :
        1. Si Conso > Seuil_Blanc+Rouge :
           - Si Conso > Seuil_Rouge ET dans Calendrier_rouge → ROUGE
           - Sinon si dans Calendrier_blanc → BLANC
           - Sinon → BLEU
        2. Sinon → BLEU

        Les probabilités sont calculées en fonction de la distance aux seuils,
        avec une courbe progressive (sigmoïde) pour des résultats plus nuancés.

        Returns:
            Tuple (prob_blue, prob_white, prob_red) en pourcentages
        """
        import math

        days_remaining = max(1, TOTAL_DAYS - day_in_season)
        target_date = self.get_season_start(date.today()) + timedelta(days=day_in_season - 1)
        is_sunday = target_date.weekday() == 6

        # ══════════════════════════════════════════════════════════════════════
        # CONTRAINTE ABSOLUE N°1 : Les dimanches sont TOUJOURS 100% bleu
        # Les jours blancs ne peuvent pas être tirés le dimanche (règle RTE)
        # ══════════════════════════════════════════════════════════════════════
        if is_sunday:
            return 100.0, 0.0, 0.0

        # Vérifier les contraintes calendaires
        in_red_calendar = self.is_in_red_calendar(target_date) and not is_weekend
        in_white_calendar = self.is_in_white_calendar(target_date, is_weekend)

        # CONTRAINTE ABSOLUE N°2 : Les weekends (samedi) ne peuvent JAMAIS être rouges
        can_be_red = in_red_calendar and red_remaining > 0 and not is_weekend
        can_be_white = in_white_calendar and white_remaining > 0

        def sigmoid_prob(distance: float, steepness: float = 2.5) -> float:
            """
            Calcule une probabilité progressive basée sur la distance au seuil.
            Utilise une sigmoïde pour une transition plus douce.

            Args:
                distance: Distance au seuil (positive = au-dessus, négative = en-dessous)
                steepness: Raideur de la courbe (plus petit = plus progressif)

            Returns:
                Probabilité entre 0 et 1
            """
            # Sigmoïde centrée sur 0.5, variant de ~0.12 à ~0.88 pour distance [-1, +1]
            return 1 / (1 + math.exp(-steepness * distance))

        if normalized_consumption is not None:
            # ══════════════════════════════════════════════════════════════════
            # Algorithme RTE avec données de consommation réelles
            #
            # HIÉRARCHIE DES SEUILS (RTE) :
            # - threshold_white_red (~0.9) : seuil d'entrée zone blanc/rouge
            # - threshold_red (~1.3) : seuil d'entrée zone rouge
            #
            # Donc : threshold_red > threshold_white_red
            # Échelle : BLEU < threshold_white_red < BLANC < threshold_red < ROUGE
            # ══════════════════════════════════════════════════════════════════

            # Distance relative aux seuils
            dist_to_white_red = normalized_consumption - threshold_white_red
            dist_to_red = normalized_consumption - threshold_red

            # Écart entre les deux seuils (threshold_red > threshold_white_red)
            threshold_gap = max(0.1, threshold_red - threshold_white_red)

            # Position dans la zone intermédiaire (0 = seuil blanc, 1 = seuil rouge)
            if threshold_gap > 0.01:
                position_in_zone = dist_to_white_red / threshold_gap
            else:
                position_in_zone = 0.0

            logger.debug(
                f"[TEMPO PROB] conso_norm={normalized_consumption:.3f}, "
                f"seuil_blanc={threshold_white_red:.3f}, seuil_rouge={threshold_red:.3f}, "
                f"gap={threshold_gap:.3f}, position={position_in_zone:.3f}"
            )

            if can_be_red and dist_to_red > 0:
                # ─────────────────────────────────────────────────────────────
                # Zone ROUGE : au-dessus du seuil rouge
                # Probabilité rouge dominante, croissante avec la distance
                # Calibration Selectra : jusqu'à ~82% rouge observé
                # ─────────────────────────────────────────────────────────────
                # Distance au-dessus du seuil rouge, normalisée
                excess = min(dist_to_red / max(0.1, threshold_gap), 3.0)

                # Progression exponentielle : 70% au seuil, monte vers 92%
                # excess=0 → 70%, excess=1 → 85%, excess=2 → 90%
                prob_red = 70.0 + 22.0 * (1 - math.exp(-1.2 * excess))

                # Blanc : probabilité résiduelle
                prob_white = max(1.0, (100 - prob_red) * 0.7) if can_be_white else 0.0
                prob_blue = max(0.5, 100.0 - prob_red - prob_white)

            elif dist_to_white_red > 0:
                # ─────────────────────────────────────────────────────────────
                # Zone INTERMÉDIAIRE : entre seuil blanc+rouge et seuil rouge
                # C'est ICI que se joue la distinction blanc/rouge
                #
                # L'algorithme RTE favorise le ROUGE dans cette zone quand :
                # - On est en période rouge (nov-mars, pas weekend)
                # - Il reste des jours rouges à placer
                # - La pression de stock est forte (beaucoup de rouges à placer)
                #
                # Observation Selectra janvier 2026 :
                # - Position ~0.07 (juste au-dessus seuil) → ~67% rouge
                # - Position ~0.57 → ~75% rouge
                # ─────────────────────────────────────────────────────────────

                # Position dans la zone : 0 = juste au-dessus du seuil blanc
                #                         1 = au seuil rouge
                pos = min(position_in_zone, 1.0)

                if can_be_red:
                    # Période rouge active : favoriser le rouge dès l'entrée dans la zone
                    #
                    # Calcul de la pression de stock :
                    # - Jours restants jusqu'au 31 mars (fin période rouge)
                    # - Si red_remaining / jours_restants > 0.15, forte pression
                    days_until_march_end = max(1, (date(target_date.year if target_date.month <= 3 else target_date.year + 1, 3, 31) - target_date).days)
                    red_pressure = min(1.0, (red_remaining / days_until_march_end) * 5)  # Normalisé 0-1

                    # Probabilité rouge de base : 55% dès l'entrée dans la zone
                    # Augmente avec la position ET la pression de stock
                    # pos=0, pressure=0.5 → 55 + 10 = 65%
                    # pos=0.5, pressure=0.5 → 55 + 15 + 10 = 80%
                    # pos=1.0, pressure=0.5 → 55 + 30 + 10 = 95% (capped à 90%)
                    base_red = 55.0
                    position_bonus = pos * 30.0  # 0-30% selon position
                    pressure_bonus = red_pressure * 20.0  # 0-20% selon pression stock
                    prob_red = min(90.0, base_red + position_bonus + pressure_bonus)

                    # Probabilité blanche : résiduelle, décroissante
                    prob_white = max(2.0, (100.0 - prob_red) * 0.8) if can_be_white else 0.0

                    prob_blue = max(1.0, 100.0 - prob_white - prob_red)

                    logger.debug(
                        f"[TEMPO PROB] Zone intermédiaire: pos={pos:.2f}, "
                        f"red_pressure={red_pressure:.2f}, prob_red={prob_red:.1f}%"
                    )
                else:
                    # Hors période rouge : blanc dominant
                    prob_red = 0.0
                    prob_white = 60.0 + pos * 25.0 if can_be_white else 0.0  # 60% → 85%
                    prob_blue = max(0.0, 100.0 - prob_white)

            else:
                # ─────────────────────────────────────────────────────────────
                # Zone BLEUE : sous le seuil blanc+rouge
                # Calibration Selectra : ~67% bleu pour jours froids mais pas critiques
                # ─────────────────────────────────────────────────────────────
                # Distance en dessous du seuil (positive = bien en dessous)
                dist_below = -dist_to_white_red

                # Plus on est loin en dessous, plus c'est bleu
                # Progression linéaire : 55% (proche seuil) → 95% (loin du seuil)
                norm_dist = min(dist_below / max(0.1, threshold_gap), 2.0)
                prob_blue = 55.0 + 40.0 * min(1.0, norm_dist)

                # Probabilités résiduelles si proche du seuil
                remaining = 100.0 - prob_blue
                if can_be_white and can_be_red:
                    # Répartition : plus de blanc que de rouge
                    prob_white = remaining * 0.65
                    prob_red = remaining * 0.35
                elif can_be_white:
                    prob_white = remaining * 0.9
                    prob_red = 0.0
                elif can_be_red:
                    prob_white = 0.0
                    prob_red = remaining * 0.35
                    prob_blue += remaining * 0.65
                else:
                    prob_white = remaining
                    prob_red = 0.0

        else:
            # ══════════════════════════════════════════════════════════════════
            # Estimation sans données RTE : utilise les quotas restants
            # ══════════════════════════════════════════════════════════════════

            # Probabilités de base selon les quotas restants
            if days_remaining > 0:
                prob_blue = (blue_remaining / days_remaining) * 100
                prob_white = (white_remaining / days_remaining) * 100 if can_be_white else 0
                prob_red = (red_remaining / days_remaining) * 100 if can_be_red else 0
            else:
                prob_blue, prob_white, prob_red = 82.2, 11.8, 6.0

            # Ajustements saisonniers
            if is_winter and can_be_red:
                # En hiver, les jours rouge/blanc sont plus probables
                if prob_blue > 55:
                    transfer = min(30, prob_blue - 55)
                    prob_blue -= transfer
                    prob_white += transfer * 0.55
                    prob_red += transfer * 0.45
            elif not is_winter:
                # Hors période rouge, transférer rouge vers bleu
                if prob_red > 0:
                    prob_blue += prob_red * 0.8
                    prob_white += prob_red * 0.2
                    prob_red = 0

            # Weekends (samedi) : jamais rouge, probabilité bleu plus élevée
            # Observation Selectra 17/01/2026 : ~71% bleu, ~30% blanc pour un samedi
            if is_weekend:
                if prob_red > 0:
                    prob_blue += prob_red * 0.7
                    prob_white += prob_red * 0.3
                    prob_red = 0
                # Boost bleu significatif pour les samedis (RTE les évite pour blanc/rouge)
                if prob_blue < 70:
                    deficit = 70 - prob_blue
                    prob_blue = 70
                    prob_white = max(0, prob_white - deficit)

        # ══════════════════════════════════════════════════════════════════════
        # Contraintes finales de stock
        # ══════════════════════════════════════════════════════════════════════
        if red_remaining <= 0 and prob_red > 0:
            prob_blue += prob_red * 0.5
            prob_white += prob_red * 0.5
            prob_red = 0

        if white_remaining <= 0 and prob_white > 0:
            prob_blue += prob_white
            prob_white = 0

        # Contrainte calendaire finale : pas de rouge hors nov-mars ou weekend
        if (not in_red_calendar or is_weekend) and prob_red > 0:
            prob_blue += prob_red * 0.8
            prob_white += prob_red * 0.2
            prob_red = 0

        # ══════════════════════════════════════════════════════════════════════
        # Normalisation finale (total = 100%)
        # ══════════════════════════════════════════════════════════════════════
        total = prob_blue + prob_white + prob_red
        if total > 0:
            prob_blue = round((prob_blue / total) * 100, 1)
            prob_white = round((prob_white / total) * 100, 1)
            prob_red = round(100 - prob_blue - prob_white, 1)
        else:
            prob_blue, prob_white, prob_red = 82.2, 11.8, 6.0

        # ══════════════════════════════════════════════════════════════════════
        # Ajustement samedi APRÈS normalisation (Selectra: ~71% bleu, ~30% blanc)
        # Le samedi est traité différemment car RTE évite de l'utiliser pour blanc
        # ══════════════════════════════════════════════════════════════════════
        if is_weekend and not is_sunday:
            # Samedi : boost vers bleu (~70%), reste en blanc (~30%)
            if prob_blue < 70:
                transfer = min(70 - prob_blue, prob_white)
                prob_blue += transfer
                prob_white -= transfer
            # S'assurer que le total reste 100%
            prob_red = max(0, 100.0 - prob_blue - prob_white)

        return max(0, prob_blue), max(0, prob_white), max(0, prob_red)

    def get_confidence_level(
        self,
        prob_blue: float,
        prob_white: float,
        prob_red: float,
        days_ahead: int,
        has_consumption_data: bool,
        is_sunday: bool = False,
    ) -> str:
        """Détermine le niveau de confiance de la prédiction"""
        # Dimanches : confiance maximale car c'est une contrainte RTE absolue
        # (jamais de jour blanc ou rouge le dimanche)
        if is_sunday:
            return "high"

        max_prob = max(prob_blue, prob_white, prob_red)

        # Confiance plus élevée avec données RTE réelles
        if has_consumption_data:
            if days_ahead <= 2:
                return "high" if max_prob >= 65 else "medium" if max_prob >= 45 else "low"
            elif days_ahead <= 5:
                return "high" if max_prob >= 70 else "medium" if max_prob >= 50 else "low"
            else:
                return "medium" if max_prob >= 60 else "low"
        else:
            # Sans données, confiance plus basse
            if days_ahead <= 2:
                return "medium" if max_prob >= 70 else "low"
            else:
                return "low"

    async def get_forecasts(
        self,
        days_ahead: int,
        blue_used: int,
        white_used: int,
        red_used: int,
        reference_date: date | None = None,
    ) -> list[TempoDayForecast]:
        """
        Génère les prévisions Tempo pour les N prochains jours

        Args:
            days_ahead: Nombre de jours à prévoir (max 6)
            blue_used: Jours bleus déjà utilisés cette saison
            white_used: Jours blancs déjà utilisés cette saison
            red_used: Jours rouges déjà utilisés cette saison
            reference_date: Date de référence (défaut: aujourd'hui)

        Returns:
            Liste de prévisions TempoDayForecast (J+1 à J+6)
        """
        # Limite à 6 jours : au-delà, les données RTE (weekly_forecast) deviennent
        # trop incertaines et l'API ne fournit pas de prévisions éoliennes
        days_ahead = min(days_ahead, 6)

        if reference_date is None:
            reference_date = date.today()

        # Quotas restants
        blue_remaining = max(0, QUOTA_BLEU - blue_used)
        white_remaining = max(0, QUOTA_BLANC - white_used)
        red_remaining = max(0, QUOTA_ROUGE - red_used)

        # Récupérer les prévisions de consommation RTE
        end_date = reference_date + timedelta(days=days_ahead)
        consumption_data: dict[str, dict[str, Any]] = {}
        generation_data: dict[str, dict[str, float]] = {}

        # Structures temporaires pour accumuler les valeurs (plusieurs par jour)
        daily_consumption_values: dict[str, list[float]] = {}
        daily_generation_values: dict[str, dict[str, list[float]]] = {}

        try:
            # Prévisions court terme (D-1, D-2) - valeurs horaires en MW
            short_term = await self.fetch_consumption_forecast(reference_date, end_date)
            for forecast in short_term:
                forecast_type = forecast.get("type", "UNKNOWN")
                for value in forecast.get("values", []):
                    dt = datetime.fromisoformat(value["start_date"])
                    date_key = dt.strftime("%Y-%m-%d")
                    if date_key not in daily_consumption_values:
                        daily_consumption_values[date_key] = []
                        consumption_data[date_key] = {"forecast_type": forecast_type}
                    daily_consumption_values[date_key].append(value.get("value", 0))

            # Prévisions hebdomadaires (J+3 à J+9) - valeurs horaires en MW
            weekly = await self.fetch_weekly_forecast()
            for forecast in weekly:
                for value in forecast.get("values", []):
                    dt = datetime.fromisoformat(value["start_date"])
                    date_key = dt.strftime("%Y-%m-%d")
                    if date_key not in daily_consumption_values:
                        daily_consumption_values[date_key] = []
                        consumption_data[date_key] = {"forecast_type": "WEEKLY"}
                    daily_consumption_values[date_key].append(value.get("value", 0))

            # Prévisions de production (solaire, éolien) - valeurs horaires en MW
            generation = await self.fetch_generation_forecast(reference_date, end_date)
            for forecast in generation:
                prod_type = forecast.get("production_type", "")
                for value in forecast.get("values", []):
                    dt = datetime.fromisoformat(value["start_date"])
                    date_key = dt.strftime("%Y-%m-%d")
                    if date_key not in daily_generation_values:
                        daily_generation_values[date_key] = {"solar": [], "wind": []}

                    if prod_type == "SOLAR":
                        daily_generation_values[date_key]["solar"].append(value.get("value", 0))
                    elif prod_type in ["WIND_ONSHORE", "WIND_OFFSHORE"]:
                        daily_generation_values[date_key]["wind"].append(value.get("value", 0))

            # Calculer la MOYENNE de consommation journalière (selon méthode RTE)
            # Document RTE page 2 : "La grandeur utilisée dans l'algorithme est la
            # consommation nette moyenne journalière, sur des journées de type Tempo (06h – 06h)"
            for date_key, values in daily_consumption_values.items():
                if values:
                    # Moyenne de consommation = moyenne des valeurs du jour
                    avg_consumption = sum(values) / len(values)
                    consumption_data[date_key]["consumption_mw"] = avg_consumption
                    logger.debug(
                        f"[TEMPO FORECAST] {date_key}: "
                        f"moy={avg_consumption:.0f}MW, pic={max(values):.0f}MW, "
                        f"nb_valeurs={len(values)}"
                    )

            # Calculer la production moyenne journalière (solaire + éolien)
            for date_key, values in daily_generation_values.items():
                solar_avg = sum(values["solar"]) / len(values["solar"]) if values["solar"] else 0
                wind_avg = sum(values["wind"]) / len(values["wind"]) if values["wind"] else 0
                generation_data[date_key] = {"solar": solar_avg, "wind": wind_avg}

        except Exception as e:
            logger.warning(f"[TEMPO FORECAST] Error fetching RTE data: {e}")

        forecasts = []

        for i in range(1, days_ahead + 1):
            target_date = reference_date + timedelta(days=i)
            date_key = target_date.isoformat()
            day_in_season = self.get_day_in_season(target_date)

            # Période hivernale et type de jour
            is_winter = target_date.month in [11, 12, 1, 2, 3]
            is_weekend = target_date.weekday() >= 5
            is_sunday = target_date.weekday() == 6  # Dimanche = weekday 6

            # Calcul des seuils
            threshold_white_red, threshold_red = self.calculate_thresholds(
                day_in_season, white_remaining, red_remaining
            )

            # Calcul de la consommation nette normalisée si données disponibles
            normalized_consumption = None
            forecast_type = "ESTIMATED"

            if date_key in consumption_data:
                cons = consumption_data[date_key]["consumption_mw"]
                gen = generation_data.get(date_key, {"solar": 0, "wind": 0})
                net_consumption = cons - gen["solar"] - gen["wind"]
                normalized_consumption = self.normalize_consumption(net_consumption)
                forecast_type = consumption_data[date_key]["forecast_type"]

                logger.debug(
                    f"[TEMPO] {date_key}: conso_nette={net_consumption:.0f}MW, "
                    f"normalisée={normalized_consumption:.2f}"
                )

            # Calcul des probabilités
            prob_blue, prob_white, prob_red = self.calculate_probabilities(
                normalized_consumption,
                threshold_white_red,
                threshold_red,
                day_in_season,
                is_winter,
                is_weekend,
                blue_remaining,
                white_remaining,
                red_remaining,
                is_sunday,
            )

            # Couleur la plus probable
            probs = {"BLUE": prob_blue, "WHITE": prob_white, "RED": prob_red}
            most_likely = max(probs, key=lambda x: probs[x])

            # Niveau de confiance
            # Dimanches = "high" car c'est une contrainte RTE absolue (100% bleu)
            confidence = self.get_confidence_level(
                prob_blue, prob_white, prob_red, i, normalized_consumption is not None, is_sunday
            )

            # Facteurs explicatifs
            factors = {
                "is_winter": is_winter,
                "is_weekend": is_weekend,
                "days_remaining_in_season": TOTAL_DAYS - day_in_season,
                "blue_remaining": blue_remaining,
                "white_remaining": white_remaining,
                "red_remaining": red_remaining,
                "has_rte_data": normalized_consumption is not None,
            }

            forecast = TempoDayForecast(
                date=date_key,
                day_in_season=day_in_season,
                probability_blue=prob_blue,
                probability_white=prob_white,
                probability_red=prob_red,
                most_likely=most_likely,
                confidence=confidence,
                threshold_white_red=round(threshold_white_red, 3),
                threshold_red=round(threshold_red, 3),
                normalized_consumption=round(normalized_consumption, 3) if normalized_consumption else None,
                forecast_type=forecast_type,
                factors=factors,
            )

            forecasts.append(forecast)

            # Mise à jour des quotas pour le jour suivant
            if most_likely == "BLUE":
                blue_remaining = max(0, blue_remaining - 1)
            elif most_likely == "WHITE":
                white_remaining = max(0, white_remaining - 1)
            elif most_likely == "RED":
                red_remaining = max(0, red_remaining - 1)

        return forecasts


# Singleton
tempo_forecast_service = TempoForecastService()
