from datetime import datetime, timezone
from config import FOOTBALL_DATA_API_KEY
import os

import requests

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
        "Team_Logos",
        filename,
    )
    
    if os.path.exists(image_path):
        # Rückgabe als URL-Pfad für das Template
        return f"/static/images/Team_Logos/{filename}"
    
    return None


def fetch_team_matches(team_id=4):
    """
    Fetches matches for any Bundesliga team from football-data.org and returns
    a list compatible with the existing Jinja template in matches.html.
    """
    api_key = FOOTBALL_DATA_API_KEY
    if not api_key:
        return []

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
        response.raise_for_status()
    except requests.RequestException:
        return []

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
                # matches.html expects index 1, so we provide a 2-item list.
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

    return past_matches[-4:] + future_matches


def fetch_bundesliga_table():
    """
    Fetches Bundesliga standings from football-data.org and returns
    a list for display in the matches template.
    """
    api_key = FOOTBALL_DATA_API_KEY
    if not api_key:
        return []

    base_url = "https://api.football-data.org/v4"
    headers = {"X-Auth-Token": api_key}

    try:
        response = requests.get(
            f"{base_url}/competitions/BL1/standings",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    payload = response.json()
    standings = payload.get("standings", [])
    if not standings:
        return []

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

    return transformed_table

# Keep legacy alias
fetch_bvb_matches = fetch_team_matches

if __name__ == "__main__":
    bvb_matches = fetch_team_matches()
    for match in bvb_matches:
        print(match)