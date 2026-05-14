"""Bundesliga-Daten: Vereinsspiele und Tabelle via OpenLigaDB."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os

import requests
from pytz import timezone as pytz_timezone
from dotenv import load_dotenv

from ._openligadb_common import (
    GERMAN_WEEKDAY_ABBR,
    _OPENLIGADB_BASE,
    _parse_match_datetime,
)

# Importiere Champions League Logo-Überschreibungen für internationale Teams
try:
    from .get_champions_league_data import _CL_LOGO_OVERRIDES
except ImportError:
    _CL_LOGO_OVERRIDES = {}

load_dotenv()


# ---------------------------------------------------------------------------
# Team-Logo-Mapping (lokale Dateien)
# ---------------------------------------------------------------------------

TEAM_LOGO_MAPPING = {
    "Borussia Dortmund": "Dortmund.png",
    "FC Bayern München": "Bayern.png",
    "1. FC Köln": "Köln.png",
    "RB Leipzig": "Leipzig.png",
    "VfB Stuttgart": "Stuttgart.png",
    "TSG Hoffenheim": "Hoffenheim.png",
    "Bayer 04 Leverkusen": "Leverkusen.png",
    "Eintracht Frankfurt": "Frankfurt.png",
    "SC Freiburg": "Freiburg.png",
    "1. FSV Mainz 05": "Mainz.png",
    "1. FC Union Berlin": "Union_Berlin.png",
    "FC Augsburg": "Augsburg.png",
    "Hamburger SV": "HSV.png",
    "Borussia Mönchengladbach": "Borussia_Mönchengladbach.png",
    "SV Werder Bremen": "Werder.png",
    "FC St. Pauli": "Pauli.png",
    "VfL Wolfsburg": "Wolfsburg.png",
    "1. FC Heidenheim 1846": "Heidenheim.png",
}


def get_team_logo_path(team_name):
    """Gibt den statischen Pfad zum lokalen Team-Logo zurück (oder None)."""
    if team_name not in TEAM_LOGO_MAPPING:
        return None
    filename = TEAM_LOGO_MAPPING[team_name]
    image_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "static",
        "images",
        "BL_Team_Logos",
        filename,
    )
    if os.path.exists(image_path):
        return f"/static/images/BL_Team_Logos/{filename}"
    return None


def get_team_logo(team_name, api_logo_url=None):
    """Gibt die beste verfügbare Logo-URL für ein Team zurück.
    
    Prüft in folgender Reihenfolge:
    1. Lokale Bundesliga-Logos (für deutsche Teams)
    2. Champions League Logo-Überschreibungen (für internationale Teams)
    3. API Logo-URL (Fallback)
    """
    # Zuerst lokale Bundesliga-Logos prüfen
    local_logo = get_team_logo_path(team_name)
    if local_logo:
        return local_logo
    
    # Dann Champions League Logo-Überschreibungen prüfen
    if team_name in _CL_LOGO_OVERRIDES:
        return _CL_LOGO_OVERRIDES[team_name]
    
    # Fallback auf API Logo-URL
    return api_logo_url


# ---------------------------------------------------------------------------
# Wettbewerbe für Vereinsspiele
# ---------------------------------------------------------------------------

_COMPETITION_SHORTCUTS = ["bl1", "dfb", "ucl"]

_COMPETITION_LOGO_MAPPING = {
    "bl1": "/static/images/Competition_Logo/Bundesliga.png",
    "dfb": "/static/images/Competition_Logo/DFB_pokal.png",
    "ucl": "/static/images/Competition_Logo/champions_league_silber.png",
}


# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------

_bundesliga_table_cache = {"data": [], "fetched_at": None}
TABLE_CACHE_TTL_SECONDS = 300  # 5 Minuten

_team_matches_cache = {}
TEAM_MATCHES_CACHE_TTL_SECONDS = 60  # 1 Minute


def _get_cached_bundesliga_table(now_utc=None):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    fetched_at = _bundesliga_table_cache["fetched_at"]
    if fetched_at is None:
        return None
    if (now_utc - fetched_at).total_seconds() >= TABLE_CACHE_TTL_SECONDS:
        return None
    return _bundesliga_table_cache["data"]


def _set_cached_bundesliga_table(table_data, now_utc=None):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    _bundesliga_table_cache["data"] = table_data
    _bundesliga_table_cache["fetched_at"] = now_utc


# ---------------------------------------------------------------------------
# Saison
# ---------------------------------------------------------------------------

def _current_season_year(now_utc=None):
    """Gibt das Startjahr der aktuellen Bundesliga-Saison zurück (Grenze: August)."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    return now_utc.year if now_utc.month >= 8 else now_utc.year - 1


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def _fetch_competition_matches(shortcut, season):
    """Ruft alle Spiele eines Wettbewerbs ab (ohne Gruppen-Filter)."""
    try:
        resp = requests.get(
            f"{_OPENLIGADB_BASE}/getmatchdata/{shortcut}/{season}",
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Öffentliche Funktionen
# ---------------------------------------------------------------------------

def fetch_team_matches(team_id=7):
    """Ruft alle Spiele eines Vereins aus mehreren Wettbewerben ab.

    team_id: teamInfoId von OpenLigaDB (Standard: 7 = Borussia Dortmund).
    Gibt ein Tuple (matches_list, is_rate_limited) zurück.
    """
    now_utc = datetime.now(timezone.utc)
    cached_entry = _team_matches_cache.get(team_id)
    if cached_entry is not None:
        if (now_utc - cached_entry["fetched_at"]).total_seconds() < TEAM_MATCHES_CACHE_TTL_SECONDS:
            return cached_entry["data"], False

    season = _current_season_year(now_utc)
    local_tz = pytz_timezone("Europe/Berlin")

    with ThreadPoolExecutor(max_workers=len(_COMPETITION_SHORTCUTS)) as executor:
        futures = {
            shortcut: executor.submit(_fetch_competition_matches, shortcut, season)
            for shortcut in _COMPETITION_SHORTCUTS
        }
        competition_results = {k: f.result() for k, f in futures.items()}

    seen_match_ids = set()
    raw_team_matches = []
    for shortcut, matches in competition_results.items():
        for m in matches:
            mid = m.get("matchID")
            if mid is None or mid in seen_match_ids:
                continue
            seen_match_ids.add(mid)
            if (
                m.get("team1", {}).get("teamId") == team_id
                or m.get("team2", {}).get("teamId") == team_id
            ):
                raw_team_matches.append((shortcut, m))

    transformed_matches = []
    for shortcut, match in raw_team_matches:
        match_dt = _parse_match_datetime(match)
        if match_dt is None:
            continue

        match_dt_local = match_dt.astimezone(local_tz)
        weekday_abbr = GERMAN_WEEKDAY_ABBR[match_dt_local.weekday()]
        formatted_date_time = f"{weekday_abbr} {match_dt_local.strftime('%H:%M - %d.%m.%Y')}"

        match_results = match.get("matchResults", [])
        final_result = next(
            (r for r in match_results if r.get("resultTypeID") == 2), None
        )
        if final_result is None and match_results:
            final_result = max(match_results, key=lambda r: r.get("resultOrderID", 0))

        if final_result:
            home_score = final_result.get("pointsTeam1", "-")
            away_score = final_result.get("pointsTeam2", "-")
        else:
            home_score = "-"
            away_score = "-"

        home_team_name = match.get("team1", {}).get("teamName", "Unbekannt")
        away_team_name = match.get("team2", {}).get("teamName", "Unbekannt")
        status = "FINISHED" if match.get("matchIsFinished") else "SCHEDULED"

        try:
            season_start_year = int(match.get("leagueSeason", ""))
        except (ValueError, TypeError):
            season_start_year = None

        transformed_matches.append({
            "team1": {
                "teamName": home_team_name,
                "logo": get_team_logo(home_team_name, match.get("team1", {}).get("teamIconUrl")),
            },
            "team2": {
                "teamName": away_team_name,
                "logo": get_team_logo(away_team_name, match.get("team2", {}).get("teamIconUrl")),
            },
            "matchDateTime": match_dt.isoformat(),
            "formattedDateTime": formatted_date_time,
            "matchResults": [
                {"pointsTeam1": home_score, "pointsTeam2": away_score},
                {"pointsTeam1": home_score, "pointsTeam2": away_score},
            ],
            "status": status,
            "seasonStartYear": season_start_year,
            "competitionLogo": _COMPETITION_LOGO_MAPPING.get(shortcut),
        })

    transformed_matches.sort(key=lambda m: m["matchDateTime"])
    season_matches = [m for m in transformed_matches if m.get("seasonStartYear") == season]
    past_matches = [m for m in season_matches if datetime.fromisoformat(m["matchDateTime"]) < now_utc]
    future_matches = [m for m in season_matches if datetime.fromisoformat(m["matchDateTime"]) >= now_utc]

    result = past_matches[-4:] + future_matches
    _team_matches_cache[team_id] = {"data": result, "fetched_at": now_utc}
    return result, False


def fetch_bundesliga_table():
    """Ruft die aktuelle Bundesliga-Tabelle ab.

    Gibt ein Tuple (standings_list, is_rate_limited) zurück.
    """
    now_utc = datetime.now(timezone.utc)
    cached_table = _get_cached_bundesliga_table(now_utc)
    if cached_table is not None:
        return cached_table, False

    season = _current_season_year(now_utc)

    try:
        resp = requests.get(
            f"{_OPENLIGADB_BASE}/getbltable/bl1/{season}",
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return [], False

    rows = resp.json()
    transformed_table = []
    for idx, row in enumerate(rows):
        team_name = row.get("teamName", "Unbekannt")
        transformed_table.append({
            "position": idx + 1,
            "teamId": row.get("teamInfoId"),
            "teamName": team_name,
            "logo": get_team_logo(team_name, row.get("teamIconUrl")),
            "playedGames": row.get("matches", 0),
            "goalDifference": row.get("goalDiff", 0),
            "points": row.get("points", 0),
        })

    _set_cached_bundesliga_table(transformed_table, now_utc)
    return transformed_table, False


# Legacy-Alias
fetch_bvb_matches = fetch_team_matches
