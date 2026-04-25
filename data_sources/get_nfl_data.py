from datetime import datetime, timezone
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()
_API_KEYS = [k for k in [
    os.environ.get("TANK01_NFL_API_KEY"),
    os.environ.get("TANK01_NFL_API_KEY_2"),
    os.environ.get("TANK01_NFL_API_KEY_3"),
] if k]
_active_key_index = 0
RAPIDAPI_HOST = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"

_teams_cache = {
    "data": [],
    "fetched_at": None,
}
_games_cache = {
    "entries": {},
}
_boxscore_cache = {}
_standings_cache = {
    "data": {},
    "fetched_at": None,
}
_roster_cache = {}

CACHE_TTL_SECONDS = 300  # 5 Minuten

# Maps NFL position abbreviations to their unit group
POSITION_UNIT_MAP = {
    # Offense
    "QB": "Offense", "RB": "Offense", "FB": "Offense", "WR": "Offense",
    "TE": "Offense", "OT": "Offense", "OG": "Offense", "C": "Offense",
    "OL": "Offense", "G": "Offense", "T": "Offense", "LT": "Offense",
    "RT": "Offense", "LG": "Offense", "RG": "Offense",
    # Defense
    "DE": "Defense", "DT": "Defense", "NT": "Defense", "LB": "Defense",
    "MLB": "Defense", "OLB": "Defense", "ILB": "Defense", "CB": "Defense",
    "S": "Defense", "FS": "Defense", "SS": "Defense", "DB": "Defense",
    "DL": "Defense",
    # Special Teams
    "K": "Special Teams", "P": "Special Teams", "LS": "Special Teams",
    "KR": "Special Teams", "PR": "Special Teams",
    "PK": "Special Teams",
}

# Display order for positions within each unit
POSITION_ORDER = {
    "Offense": ["QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "OT", "OG", "OL", "T", "G"],
    "Defense": ["DE", "DT", "NT", "DL", "MLB", "ILB", "OLB", "LB", "CB", "FS", "SS", "S", "DB"],
    "Special Teams": ["K", "P", "LS", "KR", "PR", "PK"],
}


def _classify_position(pos):
    return POSITION_UNIT_MAP.get((pos or "").upper(), "Offense")


def _parse_height_to_meters(height_str):
    """Convert '6\'2"' or '6-2' to meter string."""
    if not height_str:
        return ""
    m = re.match(r"(\d+)['\-](\d+)", str(height_str))
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2))
        meters = (feet * 12 + inches) * 0.0254
        return f"{meters:.2f}"
    return ""


def _parse_weight_to_kg(weight_str):
    """Convert lbs string to kg string."""
    try:
        lbs = float(str(weight_str).replace("lbs", "").strip())
        return f"{lbs * 0.453592:.1f}"
    except (TypeError, ValueError):
        return ""


def _format_bday_german(bday_str):
    """Convert MM/DD/YYYY to DD.MM.YYYY."""
    if not bday_str:
        return ""
    parts = str(bday_str).split("/")
    if len(parts) == 3:
        return f"{parts[1].zfill(2)}.{parts[0].zfill(2)}.{parts[2]}"
    return bday_str
BERLIN_TZ = ZoneInfo("Europe/Berlin")


def _default_nfl_season(now_utc):
    # NFL regular season starts in late summer; spring still belongs to previous season.
    return now_utc.year if now_utc.month >= 8 else now_utc.year - 1


def _api_headers(key=None):
    return {
        "x-rapidapi-key": key or (_API_KEYS[_active_key_index] if _API_KEYS else ""),
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }


def _api_get(url, params=None, timeout=15):
    """GET request with automatic key rotation on 429 (quota exhausted)."""
    global _active_key_index
    for attempt in range(len(_API_KEYS)):
        response = requests.get(url, headers=_api_headers(), params=params, timeout=timeout)
        if response.status_code != 429:
            return response
        # Current key hit quota – try next key if available
        if _active_key_index < len(_API_KEYS) - 1:
            _active_key_index += 1
        else:
            return response  # All keys exhausted
    return response


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_epoch_to_berlin(epoch_value):
    try:
        epoch = float(epoch_value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(BERLIN_TZ)


TEAM_LOGO_MAP = {
    "ARI": "arizona cardinals",
    "ATL": "atlanta falcons",
    "BAL": "baltimore ravens",
    "BUF": "buffalo bills",
    "CAR": "carolina panthers",
    "CHI": "chicago bears",
    "CIN": "cincinnati bengals",
    "CLE": "cleveland browns",
    "DAL": "dallas cowboys",
    "DEN": "denver broncos",
    "DET": "detroit lions",
    "GB": "green bay packers",
    "HOU": "houston texans",
    "IND": "indianapolis colts",
    "JAX": "jacksonville jaguars",
    "KC": "kansas city chiefs",
    "LAR": "la rams",
    "LAC": "los angeles chargers",
    "MIA": "miami dolphins",
    "MIN": "minnesota vikings",
    "NE": "new england patriots",
    "NO": "new orleans saints",
    "NYG": "new york giants",
    "NYJ": "new york jets",
    "LV": "oakland raiders",
    "PHI": "philadelphia eagles",
    "PIT": "pittsburgh steelers",
    "SF": "san francisco 49ers",
    "SEA": "seattle seahawks",
    "TB": "tampa bay buccaneers",
    "TEN": "tennessee titans",
    "WSH": "washington commanders",
}


def get_team_logo_path(team_name):
    """Returns the URL path to a team logo if it exists locally."""
    mapped_name = TEAM_LOGO_MAP.get(team_name, team_name)
    filename = f"{mapped_name}.png"
    image_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "static",
        "images",
        "NFL_Team_Logos",
        filename,
    )

    if os.path.exists(image_path):
        return f"/static/images/NFL_Team_Logos/{filename}"

    return None


def fetch_nfl_teams():
    """Fetch team master data including standings fields."""
    if not _API_KEYS:
        return [], False

    now_utc = datetime.now(timezone.utc)
    fetched_at = _teams_cache["fetched_at"]
    if fetched_at is not None and (now_utc - fetched_at).total_seconds() < CACHE_TTL_SECONDS:
        return _teams_cache["data"], False

    try:
        response = _api_get(
            f"https://{RAPIDAPI_HOST}/getNFLTeams",
            timeout=15,
        )

        if response.status_code == 429:
            return [], True

        response.raise_for_status()
        payload = response.json()
        teams = payload.get("body", []) if isinstance(payload, dict) else []
        if not isinstance(teams, list):
            teams = []

        _teams_cache["data"] = teams
        _teams_cache["fetched_at"] = now_utc
        return teams, False
    except requests.RequestException:
        return [], False


def _fetch_nfl_boxscore(game_id):
    now_utc = datetime.now(timezone.utc)
    cached = _boxscore_cache.get(game_id)
    if cached is not None and (now_utc - cached["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached["data"], False

    try:
        response = _api_get(
            f"https://{RAPIDAPI_HOST}/getNFLBoxScore",
            params={"gameID": game_id},
            timeout=15,
        )

        if response.status_code == 429:
            return {}, True

        response.raise_for_status()
        payload = response.json()
        box = payload.get("body", {}) if isinstance(payload, dict) else {}
        if not isinstance(box, dict):
            box = {}

        _boxscore_cache[game_id] = {"data": box, "fetched_at": now_utc}
        return box, False
    except requests.RequestException:
        return {}, False


def _extract_quarter_scores(line_score):
    if not isinstance(line_score, dict):
        return []

    home_ls = line_score.get("home", {})
    away_ls = line_score.get("away", {})
    result = []
    for q in ("Q1", "Q2", "Q3", "Q4", "OT"):
        home_q = home_ls.get(q)
        away_q = away_ls.get(q)
        if home_q is None and away_q is None:
            continue
        result.append(
            {
                "label": q,
                "home": _safe_int(home_q, 0),
                "away": _safe_int(away_q, 0),
            }
        )
    return result


def fetch_nfl_scores(season=None, week=1, season_type="reg"):
    """Fetch NFL games for a week without heavy per-game detail calls."""
    if not _API_KEYS:
        return [], False

    now_utc = datetime.now(timezone.utc)

    try:
        if season is None:
            season = _default_nfl_season(now_utc)

        cache_key = f"{season}:{week}:{season_type}"
        cached = _games_cache["entries"].get(cache_key)
        if cached is not None and (now_utc - cached["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
            return cached["data"], False

        response = _api_get(
            f"https://{RAPIDAPI_HOST}/getNFLGamesForWeek",
            params={
                "week": week,
                "season": season,
                "seasonType": season_type,
            },
            timeout=15,
        )

        if response.status_code == 429:
            return [], True

        response.raise_for_status()
        payload = response.json()
        raw_games = payload.get("body", []) if isinstance(payload, dict) else []
        if not isinstance(raw_games, list):
            raw_games = []

        transformed = []
        for game in raw_games:
            if not isinstance(game, dict):
                continue

            game_id = game.get("gameID", "")
            home_abv = game.get("home", "")
            away_abv = game.get("away", "")

            kickoff_berlin = _parse_epoch_to_berlin(game.get("gameTime_epoch"))
            kickoff_date = kickoff_berlin.strftime("%d.%m.%Y") if kickoff_berlin else "-"
            kickoff_time = kickoff_berlin.strftime("%H:%M") if kickoff_berlin else "-"

            status_code = str(game.get("gameStatusCode", ""))

            transformed.append(
                {
                    "gameID": game_id,
                    "homeTeam": home_abv,
                    "awayTeam": away_abv,
                    "homeScore": "-",
                    "awayScore": "-",
                    "week": game.get("gameWeek", ""),
                    "status": game.get("gameStatus", ""),
                    "statusCode": status_code,
                    "kickoff_date_de": kickoff_date,
                    "kickoff_time_de": kickoff_time,
                    "homeTeamLogo": get_team_logo_path(home_abv),
                    "awayTeamLogo": get_team_logo_path(away_abv),
                    "quarters": [],
                }
            )

        _games_cache["entries"][cache_key] = {
            "data": transformed,
            "fetched_at": now_utc,
        }
        return transformed, False
    except requests.RequestException:
        return [], False


def enrich_matches_with_boxscores(matches):
    """Enrich only the given matches with boxscore totals and quarter splits."""
    if not matches:
        return [], False

    enriched = [dict(match) for match in matches]
    rate_limited = False

    jobs = []
    for index, match in enumerate(enriched):
        game_id = match.get("gameID", "")
        status_code = str(match.get("statusCode", ""))
        if status_code in {"1", "2"} and game_id:
            jobs.append((index, game_id))

    if not jobs:
        return enriched, False

    max_workers = min(16, len(jobs))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_fetch_nfl_boxscore, game_id): index
            for index, game_id in jobs
        }

        for future in as_completed(future_map):
            index = future_map[future]
            try:
                boxscore, box_rate_limited = future.result()
            except Exception:
                boxscore, box_rate_limited = {}, False

            rate_limited = rate_limited or box_rate_limited

            if boxscore:
                enriched[index]["homeScore"] = _safe_int(boxscore.get("homePts"), "-")
                enriched[index]["awayScore"] = _safe_int(boxscore.get("awayPts"), "-")
                enriched[index]["quarters"] = _extract_quarter_scores(boxscore.get("lineScore", {}))

    return enriched, rate_limited


def fetch_nfl_standings(season=None):
    """Build standings from getNFLTeams endpoint."""
    del season  # endpoint returns current standings

    now_utc = datetime.now(timezone.utc)
    fetched_at = _standings_cache["fetched_at"]
    if fetched_at is not None and (now_utc - fetched_at).total_seconds() < CACHE_TTL_SECONDS:
        return _standings_cache["data"], False

    teams, rate_limited = fetch_nfl_teams()
    if rate_limited:
        return {}, True
    if not teams:
        return {}, False

    standings = build_nfl_standings_from_teams(teams)
    if not standings:
        return {}, False

    _standings_cache["data"] = standings
    _standings_cache["fetched_at"] = now_utc
    return standings, False


def build_nfl_standings_from_teams(teams):
    """Build standings structure from raw team list."""
    if not teams:
        return {}

    standings = {}
    for team in teams:
        conf = team.get("conferenceAbv", "N/A")
        div = team.get("division", "N/A")

        wins = _safe_int(team.get("wins"), 0)
        losses = _safe_int(team.get("loss"), 0)
        ties = _safe_int(team.get("tie"), 0)
        played = wins + losses + ties
        pct = (wins + 0.5 * ties) / played if played > 0 else 0.0

        team_row = {
            "abv": team.get("teamAbv", ""),
            "name": f"{team.get('teamCity', '').strip()} {team.get('teamName', '').strip()}".strip(),
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "winPct": round(pct, 3),
            "conference": conf,
            "division": div,
            "logo": get_team_logo_path(team.get("teamAbv", "")),
        }

        standings.setdefault(conf, {}).setdefault(div, []).append(team_row)

    for conf in standings.values():
        for div in conf.values():
            div.sort(key=lambda t: (t["winPct"], t["wins"]), reverse=True)

    return standings


def organize_matches_by_team(scores):
    """Organizes games by team abbreviation."""
    matches_by_team = {}

    if not scores:
        return matches_by_team

    for score in scores:
        home_team = score.get("homeTeam", "")
        away_team = score.get("awayTeam", "")
        match_data = {
            "homeTeam": home_team,
            "awayTeam": away_team,
            "homeScore": score.get("homeScore", "-"),
            "awayScore": score.get("awayScore", "-"),
            "week": score.get("week", ""),
            "status": score.get("status", ""),
            "kickoff_date_de": score.get("kickoff_date_de", "-"),
            "kickoff_time_de": score.get("kickoff_time_de", "-"),
            "homeTeamLogo": score.get("homeTeamLogo"),
            "awayTeamLogo": score.get("awayTeamLogo"),
            "quarters": score.get("quarters", []),
        }

        if home_team not in matches_by_team:
            matches_by_team[home_team] = []
        matches_by_team[home_team].append(match_data)

        if away_team not in matches_by_team:
            matches_by_team[away_team] = []
        matches_by_team[away_team].append(match_data)

    return matches_by_team


def format_standings_table(standings_data, conference=None, division=None):
    """
    Formats standings data for display.
    If conference/division provided, filters accordingly.
    Returns list of teams with stats.
    """
    formatted = []

    for conf_key, conf_data in standings_data.items():
        if conference and conf_key != conference:
            continue

        for div_key, div_teams in conf_data.items():
            if division and div_key != division:
                continue

            for team_data in div_teams:
                formatted.append(team_data)

    formatted.sort(key=lambda t: (t.get("winPct", 0), t.get("wins", 0)), reverse=True)
    return formatted


def get_conference_standings(standings_data, conference):
    """Gets all teams in a conference."""
    return format_standings_table(standings_data, conference=conference)


def get_division_standings(standings_data, conference, division):
    """Gets all teams in a specific division."""
    return format_standings_table(standings_data, conference=conference, division=division)


def get_complete_league_standings(standings_data):
    """Gets all teams in the league."""
    return format_standings_table(standings_data)


def fetch_nfl_team_roster(team_abv):
    """Fetch and parse the roster for a specific team."""
    if not _API_KEYS:
        return [], False

    now_utc = datetime.now(timezone.utc)
    cached = _roster_cache.get(team_abv)
    if cached is not None and (now_utc - cached["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached["data"], False

    try:
        response = _api_get(
            f"https://{RAPIDAPI_HOST}/getNFLTeamRoster",
            params={"teamAbv": team_abv},
            timeout=15,
        )

        if response.status_code == 429:
            return [], True

        response.raise_for_status()
        payload = response.json()
        body = payload.get("body", {}) if isinstance(payload, dict) else {}
        roster_raw = body.get("roster", []) if isinstance(body, dict) else []
        if not isinstance(roster_raw, list):
            roster_raw = []

        roster = []
        for player in roster_raw:
            if not isinstance(player, dict):
                continue
            pos = player.get("pos", "")
            height_str = player.get("height", "")
            roster.append({
                "longName": player.get("longName", ""),
                "age": player.get("age", ""),
                "bDay": _format_bday_german(player.get("bDay", "")),
                "height": height_str,
                "height_m": _parse_height_to_meters(height_str),
                "weight_kg": _parse_weight_to_kg(player.get("weight", "")),
                "jerseyNum": player.get("jerseyNum", ""),
                "school": player.get("school", ""),
                "pos": pos,
                "unit": _classify_position(pos),
            })

        _roster_cache[team_abv] = {"data": roster, "fetched_at": now_utc}
        return roster, False
    except requests.RequestException:
        return [], False
