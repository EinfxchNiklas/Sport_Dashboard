import requests
import pandas as pd
from bs4 import BeautifulSoup


def get_bvb_fixtures():
    """Holt die nächsten Spiele von Borussia Dortmund von kicker.de"""
    url = "https://www.kicker.de/borussia-dortmund/spielplan"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.kicker.de/"
    }
    r = requests.get(url, headers=headers)
    
    #Debug Ausgabe
    print("Status Code:", r.status_code)
    print("HTML Vorschau:", r.text[:1000])
    soup = BeautifulSoup(r.text, "lxml")

    data = []
    rows = soup.select("tr")  # jede Tabellenzeile = ein Spiel
    for row in rows:
        # Datum
        date_cell = row.select_one("td.kick__table--gamelist_date")
        date = date_cell.get_text(strip=True) if date_cell else ""

        # Teams
        teams = [t.get_text(strip=True) for t in row.select("div.kick__v100-gameCell__team__name")]
        matchup = " vs ".join(teams) if teams else ""

        # Ergebnis
        result_cell = row.select_one("a.kick__v100-scoreBoard")
        result = result_cell.get_text(strip=True) if result_cell else "-"

        if date or matchup:
            data.append([date, matchup, result])

    return pd.DataFrame(data, columns=["Datum", "Teams", "Ergebnis"])


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
