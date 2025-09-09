import requests
import pandas as pd
from bs4 import BeautifulSoup


BASE_URL = "https://api.openligadb.de"

def get_bvb_matches(season=2024):
    """Lädt den Spielplan von Borussia Dortmund für eine Saison."""
    url = f"{BASE_URL}/getmatchdata/bl1/{season}/borussia-dortmund"
    response = requests.get(url)
    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json()
    matches = []

    for match in data:
        home = match["Team1"]["TeamName"]
        away = match["Team2"]["TeamName"]
        date = match["MatchDateTime"]

        # Ergebnis prüfen
        result = ""
        if match["MatchIsFinished"]:
            goals_home = match["MatchResults"][-1]["PointsTeam1"]
            goals_away = match["MatchResults"][-1]["PointsTeam2"]
            result = f"{goals_home}:{goals_away}"
        else:
            result = "Noch nicht gespielt"

        matches.append({
            "Datum": date[:10],
            "Heim": home,
            "Auswärts": away,
            "Ergebnis": result
        })

    return pd.DataFrame(matches)


def get_bvb_injuries():
    """Holt verletzte Spieler von Borussia Dortmund (transfermarkt.de)"""
    url = "https://www.transfermarkt.de/borussia-dortmund/sperrenundverletzungen/verein/16"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    data = []
    table = soup.select_one("table.items")
    if not table:
        return pd.DataFrame(columns=["Spieler", "Verletzung", "Seit", "Voraussichtlich bis"])

    rows = table.select("tr")
    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.select("td")]
        if len(cols) >= 4:
            spieler = cols[0]
            verletzung = cols[1]
            seit = cols[2]
            bis = cols[3]
            data.append([spieler, verletzung, seit, bis])

    return pd.DataFrame(data, columns=["Spieler", "Verletzung", "Seit", "Voraussichtlich bis"])
