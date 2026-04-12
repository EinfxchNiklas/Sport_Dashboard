from datetime import datetime, timezone
import os
import requests

from dotenv import load_dotenv

load_dotenv()
FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY')

# Mapping von Team-Namen zu lokalen Bild-Dateinamen (im static/images/ Ordner)
TEAM_LOGO_MAPPING = {
    "Borussia Dortmund": "Dortmund.png",
    "FC Bayern München": "Bayern.png",
    "1. FC Köln": "Köln.png",
    "RB Leipzig": "Leipzig.png",
    "VfB Stuttgart": "Stuttgart.png",
    "TSG 1899 Hoffenheim": "Hoffenheim.png",
    "Bayer 04 Leverkusen": "Leverkusen.png",
    "Eintracht Frankfurt": "Frankfurt.png",
    "SC Freiburg": "Freiburg.png",
    "1. FSV Mainz 05": "Mainz.png",
    "1. FC Union Berlin": "Union_Berlin.png",
    "FC Augsburg": "Augsburg.png",
    "Hamburger SV": "HSV.png",
    "Borussia Mönchengladbach": "Borussia_Mönchengladbach.png",
    "SV Werder Bremen": "Werder.png",
    "FC St. Pauli 1910": "Pauli.png",
    "VfL Wolfsburg": "Wolfsburg.png",
    "1. FC Heidenheim 1846": "Heidenheim.png",
}

_bundesliga_table_cache = {
    "data": [],
    "fetched_at": None,
}
TABLE_CACHE_TTL_SECONDS = 300  # 5 Minuten

_team_matches_cache = {}  # team_id -> {"data": ..., "fetched_at": ...}
TEAM_MATCHES_CACHE_TTL_SECONDS = 60  # 1 Minute


def _get_cached_bundesliga_table(now_utc=None):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    fetched_at = _bundesliga_table_cache["fetched_at"]
    if fetched_at is None:
        return None

    cache_age_seconds = (now_utc - fetched_at).total_seconds()
    if cache_age_seconds >= TABLE_CACHE_TTL_SECONDS:
        return None

    return _bundesliga_table_cache["data"]


def _set_cached_bundesliga_table(table_data, now_utc=None):
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    _bundesliga_table_cache["data"] = table_data
    _bundesliga_table_cache["fetched_at"] = now_utc


def get_team_logo_path(team_name):
    """
    Returns the URL path to a team logo if it exists locally.
    Returns None if no logo is found.
    """
    if team_name not in TEAM_LOGO_MAPPING:
        return None
    
    filename = TEAM_LOGO_MAPPING[team_name]
    # Prüfen, ob die Datei tatsächlich existiert
    image_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "static",
        "images",
        "BL_Team_Logos",
        filename,
    )
    
    if os.path.exists(image_path):
        # Rückgabe als URL-Pfad für das Template
        return f"/static/images/BL_Team_Logos/{filename}"
    
    return None


def fetch_team_matches(team_id=4):
    """
    Fetches matches for any Bundesliga team from football-data.org and returns
    a tuple: (matches_list, is_rate_limited)
    Returns empty list and rate_limited flag if API error occurs.
    """
    api_key = FOOTBALL_DATA_API_KEY
    if not api_key:
        return [], False

    now_utc = datetime.now(timezone.utc)
    cached_entry = _team_matches_cache.get(team_id)
    if cached_entry is not None:
        cache_age = (now_utc - cached_entry["fetched_at"]).total_seconds()
        if cache_age < TEAM_MATCHES_CACHE_TTL_SECONDS:
            return cached_entry["data"], False

    base_url = "https://api.football-data.org/v4"
    competitions = "BL1,DFB,CL,EL,UECL"

    headers = {"X-Auth-Token": api_key}
    params = {"competitions": competitions, "limit": 60}

    try:
        response = requests.get(
            f"{base_url}/teams/{team_id}/matches",
            headers=headers,
            params=params,
            timeout=15,
        )
        
        if response.status_code == 429:
            return [], True
        
        response.raise_for_status()
    except requests.RequestException:
        return [], False

    payload = response.json()
    raw_matches = payload.get("matches", [])
    now_utc = datetime.now(timezone.utc)

    # In European football, the season usually starts in July.
    current_season_start_year = now_utc.year if now_utc.month >= 7 else now_utc.year - 1

    transformed_matches = []
    for match in raw_matches:
        utc_date = match.get("utcDate")
        if not utc_date:
            continue

        try:
            match_dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        except ValueError:
            continue

        full_time = match.get("score", {}).get("fullTime", {})
        home_score = full_time.get("home") if full_time.get("home") is not None else "-"
        away_score = full_time.get("away") if full_time.get("away") is not None else "-"
        season_start = match.get("season", {}).get("startDate", "")
        season_start_year = int(season_start[:4]) if len(season_start) >= 4 and season_start[:4].isdigit() else None

        home_team_name = match.get("homeTeam", {}).get("name", "Unbekannt")
        away_team_name = match.get("awayTeam", {}).get("name", "Unbekannt")

        transformed_matches.append(
            {
                "team1": {
                    "teamName": home_team_name,
                    "logo": get_team_logo_path(home_team_name),
                },
                "team2": {
                    "teamName": away_team_name,
                    "logo": get_team_logo_path(away_team_name),
                },
                "matchDateTime": match_dt.isoformat(),
                "formattedDateTime": match_dt.astimezone().strftime("%H:%M - %d.%m.%Y"),
                # fussball.html expects index 1, so we provide a 2-item list.
                "matchResults": [
                    {"pointsTeam1": home_score, "pointsTeam2": away_score},
                    {"pointsTeam1": home_score, "pointsTeam2": away_score},
                ],
                "status": match.get("status"),
                "seasonStartYear": season_start_year,
            }
        )

    transformed_matches.sort(key=lambda m: m["matchDateTime"])

    season_matches = [
        m for m in transformed_matches
        if m.get("seasonStartYear") == current_season_start_year
    ]

    past_matches = [m for m in season_matches if datetime.fromisoformat(m["matchDateTime"]) < now_utc]
    future_matches = [m for m in season_matches if datetime.fromisoformat(m["matchDateTime"]) >= now_utc]

    result = past_matches[-4:] + future_matches
    _team_matches_cache[team_id] = {"data": result, "fetched_at": now_utc}
    return result, False


def fetch_bundesliga_table():
    """
    Fetches Bundesliga standings from football-data.org and returns
    a tuple: (standings_list, is_rate_limited)
    """
    api_key = FOOTBALL_DATA_API_KEY
    if not api_key:
        return [], False

    now_utc = datetime.now(timezone.utc)
    cached_table = _get_cached_bundesliga_table(now_utc)
    if cached_table is not None:
        return cached_table, False

    base_url = "https://api.football-data.org/v4"
    headers = {"X-Auth-Token": api_key}

    try:
        response = requests.get(
            f"{base_url}/competitions/BL1/standings",
            headers=headers,
            timeout=15,
        )
        
        if response.status_code == 429:
            return [], True
        
        response.raise_for_status()
    except requests.RequestException:
        return [], False

    payload = response.json()
    standings = payload.get("standings", [])
    if not standings:
        return [], False

    table = standings[0].get("table", [])
    transformed_table = []

    for row in table:
        team = row.get("team", {})
        team_name = team.get("name", "Unbekannt")
        transformed_table.append(
            {
                "position": row.get("position", "-"),
                "teamId": team.get("id"),
                "teamName": team_name,
                "logo": get_team_logo_path(team_name) or team.get("crest"),
                "playedGames": row.get("playedGames", 0),
                "goalDifference": row.get("goalDifference", 0),
                "points": row.get("points", 0),
            }
        )

    _set_cached_bundesliga_table(transformed_table, now_utc)

    return transformed_table, False

# Keep legacy alias
fetch_bvb_matches = fetch_team_matches

if __name__ == "__main__":
    bvb_matches, _ = fetch_team_matches()
    for match in bvb_matches:
        print(match)