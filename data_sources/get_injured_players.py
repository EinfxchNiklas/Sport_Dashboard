from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


TRANSFERMARKT_CLUB_IDS = {
    "Borussia Dortmund": 16,
    "FC Bayern München": 27,
    "1. FC Köln": 3,
    "RB Leipzig": 23826,
    "VfB Stuttgart": 79,
    "TSG Hoffenheim": 533,
    "Bayer 04 Leverkusen": 15,
    "Eintracht Frankfurt": 24,
    "SC Freiburg": 60,
    "1. FSV Mainz 05": 39,
    "1. FC Union Berlin": 89,
    "FC Augsburg": 167,
    "Hamburger SV": 41,
    "Borussia Mönchengladbach": 18,
    "SV Werder Bremen": 86,
    "FC St. Pauli": 35,
    "VfL Wolfsburg": 82,
    "1. FC Heidenheim 1846": 2036,
}

_BASE_URL = "https://www.transfermarkt.de/verein/sperrenundverletzungen/verein/{vid}"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

# Nur die Sektion mit Verletzungen berücksichtigen (keine Sperren).
_INJURY_SECTION_LABEL = "Verletzungen"


_injuries_cache = {}
INJURIES_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 Stunden


def _get_cached(team_name, now_utc):
    entry = _injuries_cache.get(team_name)
    if entry is None:
        return None
    if (now_utc - entry["fetched_at"]).total_seconds() >= INJURIES_CACHE_TTL_SECONDS:
        return None
    return entry["data"]


def _set_cached(team_name, data, now_utc):
    _injuries_cache[team_name] = {"data": data, "fetched_at": now_utc}


def _cell_text(cell):
    text = cell.get_text(" ", strip=True)
    return text if text else "-"


def _parse_injury_table(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.items")
    if table is None:
        return []

    players = []
    current_section = _INJURY_SECTION_LABEL  # Default, falls keine Sektion erscheint
    for row in table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue

        # Sektions-Kopfzeile ("Verletzungen" / "Sperren")
        if "extrarow" in (cells[0].get("class") or []):
            current_section = cells[0].get_text(strip=True)
            continue

        if current_section != _INJURY_SECTION_LABEL:
            continue
        if len(cells) < 6:
            continue

        name_cell = cells[0]
        inline = name_cell.select_one("table.inline-table")
        if inline is not None:
            inline_rows = inline.select("tr")
            if inline_rows:
                name = inline_rows[0].get_text(" ", strip=True)
                position = (
                    inline_rows[1].get_text(" ", strip=True)
                    if len(inline_rows) > 1
                    else "-"
                )
            else:
                name = name_cell.get_text(" ", strip=True)
                position = "-"
        else:
            name = name_cell.get_text(" ", strip=True)
            position = "-"
        if not name:
            continue

        players.append(
            {
                "name": name,
                "position": position or "-",
                "age": _cell_text(cells[1]),
                "injury": _cell_text(cells[2]),
                "since": _cell_text(cells[3]),
                "missedGames": _cell_text(cells[5]),
            }
        )

    players.sort(key=lambda p: p["name"].lower())
    return players


def fetch_injured_players(team_name):
    verein_id = TRANSFERMARKT_CLUB_IDS.get(team_name)
    if verein_id is None:
        return [], "unknown_team"

    now_utc = datetime.now(timezone.utc)
    cached = _get_cached(team_name, now_utc)
    if cached is not None:
        return cached, None

    url = _BASE_URL.format(vid=verein_id)
    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=20)
        if response.status_code != 200:
            return [], "fetch_failed"
        players = _parse_injury_table(response.text)
    except requests.RequestException:
        return [], "fetch_failed"

    _set_cached(team_name, players, now_utc)
    return players, None
