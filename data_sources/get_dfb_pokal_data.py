"""DFB-Pokal-Daten via OpenLigaDB (Shortcut: dfb).

Saison wird automatisch aus dem aktuellen Datum ermittelt.
"""

from pytz import timezone as pytz_timezone

from ._openligadb_common import (
    _current_football_season,
    _fetch_competition_group_matches,
    _transform_raw_match,
    _get_cached,
    _set_cached,
)


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

_DFB_SHORTCUT = "dfb"

DFB_ROUNDS = [
    {"orderID": 1, "name": "1. Runde"},
    {"orderID": 2, "name": "2. Runde"},
    {"orderID": 3, "name": "Achtelfinale"},
    {"orderID": 4, "name": "Viertelfinale"},
    {"orderID": 5, "name": "Halbfinale"},
    {"orderID": 6, "name": "Endspiel"},
]


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def fetch_dfb_data(round_order_id=1):
    """Gibt DFB-Pokal-Daten für eine bestimmte Runde zurück.

    Args:
        round_order_id: 1=1. Runde … 6=Endspiel

    Returns:
        Dict mit:
            rounds          – Liste aller Runden
            current_round_id
            matches         – Spiele der gewählten Runde
    """
    local_tz = pytz_timezone("Europe/Berlin")
    season = _current_football_season()
    cache_key = f"dfb_{season}_{round_order_id}"

    cached = _get_cached(cache_key)
    if cached:
        return cached

    raw = _fetch_competition_group_matches(_DFB_SHORTCUT, season, round_order_id)
    matches = [m for m in [_transform_raw_match(r, local_tz) for r in raw] if m]
    matches.sort(key=lambda m: m["matchDateTimeUTC"])

    result = {
        "rounds": DFB_ROUNDS,
        "current_round_id": round_order_id,
        "matches": matches,
    }
    _set_cached(cache_key, result)
    return result
