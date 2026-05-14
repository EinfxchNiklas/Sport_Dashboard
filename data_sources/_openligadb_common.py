"""Gemeinsame Hilfsfunktionen und API-Wrapper für OpenLigaDB.

Enthält:
- API-Basis-URL und generische Abfrage-Funktionen
- Datum-Parsen und Match-Transformation
- URL-Normalisierung (HTTPS, Bildgröße)
- Saison-Berechnung
- Shared In-Memory-Cache
"""

from datetime import datetime, timezone
import os
import re

import requests
from pytz import timezone as pytz_timezone
from dotenv import load_dotenv

load_dotenv()

GERMAN_WEEKDAY_ABBR = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

_OPENLIGADB_BASE = os.environ.get("OPENLIGADB_BASE_URL", "").rstrip("/")


# ---------------------------------------------------------------------------
# Saison-Helpers
# ---------------------------------------------------------------------------

def _current_football_season():
    """Gibt das Startjahr der aktuellen Fußball-Saison zurück.

    Saisons laufen von ~Juli bis Juni des Folgejahres (Grenze: Monat >= 7).
    Beispiel: Sep 2025 → 2025  (= Saison 25/26)
              Mai 2026 → 2025  (= Saison 25/26, noch laufend)
              Jul 2026 → 2026  (= neue Saison 26/27)
    """
    from datetime import date
    today = date.today()
    return today.year if today.month >= 7 else today.year - 1


# ---------------------------------------------------------------------------
# URL-Normalisierung
# ---------------------------------------------------------------------------

def _normalize_icon_url(url):
    """Normalisiert Team-Icon-URLs aus der OpenLigaDB-API.

    - Erzwingt HTTPS (verhindert Mixed-Content-Fehler im Browser)
    - Wikimedia SVG-Thumbnails → direkte SVG-Datei (Thumbnail-Service gibt 400)
    - Sonstige Wikimedia-Thumbnails → Größe auf 80 px normalisieren
    """
    if not url:
        return url
    # HTTP → HTTPS
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # SVG-Thumbnails aller Wikimedia-Namespaces in direkte SVG-Datei umwandeln.
    # Muster: .../wikipedia/{lang}/thumb/{a}/{b}/{file}.svg/{N}px-...
    # → .../wikipedia/{lang}/{a}/{b}/{file}.svg
    m = re.match(
        r'(https://upload\.wikimedia\.org/wikipedia/[^/]+)'
        r'/thumb/([0-9a-f]/[0-9a-f]{2}/[^/]+\.svg)'
        r'/\d+px-.+',
        url,
        re.IGNORECASE,
    )
    if m:
        return f'{m.group(1)}/{m.group(2)}'
    # Sonstige Wikimedia-PNG-Thumbnails auf 80 px normalisieren
    url = re.sub(
        r'(wikimedia\.org/wikipedia/[^/]+/thumb/.+?/)\d+px-',
        r'\g<1>80px-',
        url,
    )
    return url


# ---------------------------------------------------------------------------
# API-Wrapper
# ---------------------------------------------------------------------------

def _fetch_competition_group_matches(shortcut, season, group_order_id):
    """Ruft alle Spiele einer Runde/Gruppe von OpenLigaDB ab.

    Gibt eine Liste von rohen Match-Dicts zurück, bei Fehler [].
    """
    try:
        resp = requests.get(
            f"{_OPENLIGADB_BASE}/getmatchdata/{shortcut}/{season}/{group_order_id}",
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except requests.RequestException:
        return []


def _fetch_available_groups(shortcut, season):
    """Ruft die verfügbaren Gruppen/Runden eines Wettbewerbs ab."""
    try:
        resp = requests.get(
            f"{_OPENLIGADB_BASE}/getavailablegroups/{shortcut}/{season}",
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except requests.RequestException:
        return []


def _fetch_competition_table(shortcut, season):
    """Ruft die Tabelle eines Wettbewerbs ab."""
    try:
        resp = requests.get(
            f"{_OPENLIGADB_BASE}/getbltable/{shortcut}/{season}",
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Match-Transformation
# ---------------------------------------------------------------------------

def _parse_match_datetime(match):
    """Parst das Spieldatum aus einem OpenLigaDB-Match-Objekt.

    Bevorzugt matchDateTimeUTC; fällt auf matchDateTime (Europe/Berlin) zurück.
    Gibt immer ein timezone-aware datetime in UTC zurück, oder None bei Fehler.
    """
    local_tz = pytz_timezone("Europe/Berlin")

    dt_str = match.get("matchDateTimeUTC")
    if dt_str:
        try:
            if dt_str.endswith("Z"):
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    dt_str = match.get("matchDateTime")
    if dt_str:
        try:
            naive_dt = datetime.fromisoformat(dt_str)
            return local_tz.localize(naive_dt).astimezone(timezone.utc)
        except (ValueError, AttributeError):
            pass

    return None


def _get_final_result(match):
    """Gibt das Endergebnis eines Spiels zurück (None wenn noch nicht gespielt).
    
    Nimmt immer das Result mit der höchsten resultOrderID, um bei K.O.-Spielen
    (DFB-Pokal, CL, etc.) auch Verlängerung und Elfmeterschießen korrekt anzuzeigen.
    
    ResultTypes:
    - 1: Halbzeit
    - 2: Endergebnis (nach 90 Min)
    - 4: nach Verlängerung
    - 5: nach Elfmeterschießen
    """
    results = match.get("matchResults", [])
    if not results:
        return None
    # Nimm das Result mit der höchsten OrderID (= tatsächliches Endergebnis)
    return max(results, key=lambda r: r.get("resultOrderID", 0))


def _transform_raw_match(match, local_tz):
    """Wandelt ein rohes OpenLigaDB-Match-Objekt in das einheitliche Format um.

    Rückgabe-Dict:
        matchId, team1{teamId,teamName,logo}, team2{...},
        matchDateTimeUTC, matchDate, formattedDateTime,
        homeScore, awayScore, isFinished, resultType, resultName
    """
    match_dt = _parse_match_datetime(match)
    if match_dt is None:
        return None

    match_dt_local = match_dt.astimezone(local_tz)
    weekday_abbr = GERMAN_WEEKDAY_ABBR[match_dt_local.weekday()]
    formatted_date_time = (
        f"{weekday_abbr} {match_dt_local.strftime('%H:%M – %d.%m.%Y')}"
    )

    final = _get_final_result(match)
    if final:
        home_score = final.get("pointsTeam1", "-")
        away_score = final.get("pointsTeam2", "-")
        result_type_id = final.get("resultTypeID")
        result_name = final.get("resultName", "")
    else:
        home_score = "-"
        away_score = "-"
        result_type_id = None
        result_name = ""

    return {
        "matchId": match.get("matchID"),
        "team1": {
            "teamId": match.get("team1", {}).get("teamId"),
            "teamName": match.get("team1", {}).get("teamName", "Unbekannt"),
            "logo": _normalize_icon_url(match.get("team1", {}).get("teamIconUrl")),
        },
        "team2": {
            "teamId": match.get("team2", {}).get("teamId"),
            "teamName": match.get("team2", {}).get("teamName", "Unbekannt"),
            "logo": _normalize_icon_url(match.get("team2", {}).get("teamIconUrl")),
        },
        "matchDateTimeUTC": match_dt.isoformat(),
        "matchDate": match_dt_local.date(),
        "formattedDateTime": formatted_date_time,
        "homeScore": home_score,
        "awayScore": away_score,
        "isFinished": bool(match.get("matchIsFinished")),
        "resultType": result_type_id,
        "resultName": result_name,
    }


# ---------------------------------------------------------------------------
# Shared In-Memory-Cache
# ---------------------------------------------------------------------------

_competition_cache = {}
_COMPETITION_CACHE_TTL = 120  # Sekunden (2 Minuten)


def _get_cached(key):
    """Gibt gecachte Daten zurück oder None wenn abgelaufen/nicht vorhanden."""
    now = datetime.now(timezone.utc)
    entry = _competition_cache.get(key)
    if entry and (now - entry["fetched_at"]).total_seconds() < _COMPETITION_CACHE_TTL:
        return entry["data"]
    return None


def _set_cached(key, data):
    """Speichert Daten im Cache."""
    _competition_cache[key] = {"data": data, "fetched_at": datetime.now(timezone.utc)}
