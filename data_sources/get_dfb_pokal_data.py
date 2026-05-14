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

# Team-Name zu Logo-Dateinamen Mapping
# Format: "Team Name": ("Unterordner", "Dateiname")
_TEAM_LOGO_MAPPING = {
    # Bundesliga
    "FC Augsburg": ("BL_Team_Logos", "Augsburg.png"),
    "FC Bayern München": ("BL_Team_Logos", "Bayern.png"),
    "Borussia Mönchengladbach": ("BL_Team_Logos", "Borussia_Mönchengladbach.png"),
    "Borussia Dortmund": ("BL_Team_Logos", "Dortmund.png"),
    "Eintracht Frankfurt": ("BL_Team_Logos", "Frankfurt.png"),
    "SC Freiburg": ("BL_Team_Logos", "Freiburg.png"),
    "1. FC Heidenheim 1846": ("BL_Team_Logos", "Heidenheim.png"),
    "TSG 1899 Hoffenheim": ("BL_Team_Logos", "Hoffenheim.png"),
    "TSG Hoffenheim": ("BL_Team_Logos", "Hoffenheim.png"),
    "Hamburger SV": ("BL_Team_Logos", "HSV.png"),
    "1. FC Köln": ("BL_Team_Logos", "Köln.png"),
    "RB Leipzig": ("BL_Team_Logos", "Leipzig.png"),
    "Bayer 04 Leverkusen": ("BL_Team_Logos", "Leverkusen.png"),
    "1. FSV Mainz 05": ("BL_Team_Logos", "Mainz.png"),
    "FC St. Pauli": ("BL_Team_Logos", "Pauli.png"),
    "VfB Stuttgart": ("BL_Team_Logos", "Stuttgart.png"),
    "1. FC Union Berlin": ("BL_Team_Logos", "Union_Berlin.png"),
    "SV Werder Bremen": ("BL_Team_Logos", "Werder.png"),
    "VfL Wolfsburg": ("BL_Team_Logos", "Wolfsburg.png"),
    
    # 2. Bundesliga
    "DSC Arminia Bielefeld": ("BL2_Team_Logos", "arminia-bielefeld.png"),
    "Arminia Bielefeld": ("BL2_Team_Logos", "arminia-bielefeld.png"),
    "VfL Bochum": ("BL2_Team_Logos", "bochum.png"),
    "VfL Bochum 1848": ("BL2_Team_Logos", "bochum.png"),
    "SV Darmstadt 98": ("BL2_Team_Logos", "darmstadt.png"),
    "Darmstadt 98": ("BL2_Team_Logos", "darmstadt.png"),
    "SG Dynamo Dresden": ("BL2_Team_Logos", "dynamo-dresden.png"),
    "Dynamo Dresden": ("BL2_Team_Logos", "dynamo-dresden.png"),
    "Eintracht Braunschweig": ("BL2_Team_Logos", "eintracht-braunschweig.png"),
    "SV 07 Elversberg": ("BL2_Team_Logos", "elversberg.png"),
    "SV Elversberg": ("BL2_Team_Logos", "elversberg.png"),
    "Fortuna Düsseldorf": ("BL2_Team_Logos", "fortuna-dusseldorf.png"),
    "SpVgg Greuther Fürth": ("BL2_Team_Logos", "greuther-furth.png"),
    "Greuther Fürth": ("BL2_Team_Logos", "greuther-furth.png"),
    "Hannover 96": ("BL2_Team_Logos", "hannover-96.png"),
    "Hertha BSC": ("BL2_Team_Logos", "hertha-bsc.png"),
    "Holstein Kiel": ("BL2_Team_Logos", "holstein-kiel.png"),
    "1. FC Kaiserslautern": ("BL2_Team_Logos", "kaiserslautern.png"),
    "Kaiserslautern": ("BL2_Team_Logos", "kaiserslautern.png"),
    "Karlsruher SC": ("BL2_Team_Logos", "karlsruher.png"),
    "1. FC Magdeburg": ("BL2_Team_Logos", "Magedeburg.png"),
    "FC Magdeburg": ("BL2_Team_Logos", "Magedeburg.png"),
    "1. FC Nürnberg": ("BL2_Team_Logos", "nurnberg.png"),
    "FC Nürnberg": ("BL2_Team_Logos", "nurnberg.png"),
    "SC Paderborn 07": ("BL2_Team_Logos", "paderborn.png"),
    "SC Paderborn": ("BL2_Team_Logos", "paderborn.png"),
    "SC Preußen Münster": ("BL2_Team_Logos", "preussen-munster.png"),
    "Preußen Münster": ("BL2_Team_Logos", "preussen-munster.png"),
    "FC Schalke 04": ("BL2_Team_Logos", "schalke-04.png"),
    "Schalke 04": ("BL2_Team_Logos", "schalke-04.png"),
}


def _add_fallback_logos(matches):
    """Ersetzt API-Logos durch lokale Logos für Teams im Mapping."""
    for match in matches:
        for team_key in ["team1", "team2"]:
            team = match.get(team_key, {})
            team_name = team.get("teamName", "")
            
            # Für Teams im Mapping: Lokales Logo DIREKT verwenden (nicht als Fallback)
            if team_name in _TEAM_LOGO_MAPPING:
                folder, filename = _TEAM_LOGO_MAPPING[team_name]
                team["logo"] = f"/static/images/{folder}/{filename}"
    
    return matches


def fetch_dfb_data(round_order_id=1):
    """Gibt DFB-Pokal-Daten für eine bestimmte Runde zurück.

    Args:
        round_order_id: 1=1. Runde … 6=Endspiel

    Returns:
        Dict mit:
            rounds          – Liste aller Runden
            current_round_id
            matches         – Spiele der gewählten Runde
            season_label    – z.B. "2025/26"
    """
    local_tz = pytz_timezone("Europe/Berlin")
    season = _current_football_season()
    season_label = f"{season}/{(season + 1) % 100:02d}"
    cache_key = f"dfb_{season}_{round_order_id}"

    cached = _get_cached(cache_key)
    if cached:
        return cached

    raw = _fetch_competition_group_matches(_DFB_SHORTCUT, season, round_order_id)
    matches = [m for m in [_transform_raw_match(r, local_tz) for r in raw] if m]
    matches.sort(key=lambda m: m["matchDateTimeUTC"])
    
    # Fallback-Logos hinzufügen
    matches = _add_fallback_logos(matches)

    result = {
        "rounds": DFB_ROUNDS,
        "current_round_id": round_order_id,
        "matches": matches,
        "season_label": season_label,
    }
    _set_cached(cache_key, result)
    return result
