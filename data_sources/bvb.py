import requests
import pandas as pd
from bs4 import BeautifulSoup


def get_bvb_fixtures():
    """Holt die nächsten Spiele von Borussia Dortmund von kicker.de"""
    url = "https://www.kicker.de/borussia-dortmund/spielplan"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    data = []
    for match in soup.select("div.kick__card"): 
        try:
            date = match.select_one(".kick__v100-gameCell__info--datetime").get_text(strip=True)
            competition = match.select_one(".kick__v100-gameCell__competition").get_text(strip=True)
            teams = match.select_one(".kick__v100-scoreBoard__teams").get_text(" ", strip=True)
            result = match.select_one(".kick__v100-scoreBoard__score").get_text(strip=True) if match.select_one(".kick__v100-scoreBoard__score") else "-"
            data.append([date, competition, teams, result])
        except:
            continue

    return pd.DataFrame(data, columns=["Datum", "Wettbewerb", "Teams", "Ergebnis"])


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
