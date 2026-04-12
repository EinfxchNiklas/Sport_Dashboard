# Sport Dashboard

Ein Flask-basiertes Dashboard für drei Sportbereiche:
- Fußball (Bundesliga Tabelle + Teamspiele)
- Formel 1 (Rennwochenenden + Session-Ergebnisse + Championship)
- NFL (Wochen-Spiele, Standings, Team-Roster)

## Lokales Setup

### 1. Voraussetzungen
- Python 3.10+ (empfohlen)
- `pip`
- Internetzugang für API-Calls

### 2. Projekt klonen
```bash
git clone https://github.com/EinfxchNiklas/Sport_Dashboard.git
cd Sport_Dashboard
```

### 3. Virtuelle Umgebung erstellen und aktivieren
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 5. `.env` anlegen
Kopiere `.env.example` nach `.env` und setze deine Keys.

Beispiel `.env`:
```env
FOOTBALL_DATA_API_KEY=dein_football_data_key
TANK01_NFL_API_KEY=dein_tank01_key
TANK01_NFL_API_KEY_2=optional_zweiter_tank01_key
DEBUG=False
PORT=5000
```

### 6. App starten
```bash
python app.py
```
Dann im Browser oeffnen: `http://127.0.0.1:5000`

## Benötigte Umgebungsvariablen

- `FOOTBALL_DATA_API_KEY`:
  API Key für football-data.org (Fussballseite)
- `TANK01_NFL_API_KEY`:
  API Key für Tank01 NFL ueber RapidAPI
- `TANK01_NFL_API_KEY_2` (optional):
  Zweiter Key für Key-Rotation bei Rate-Limits
- `DEBUG` (optional):
  Flask Debug-Modus (`True`/`False`)
- `PORT` (optional):
  Server-Port (Default: `5000`)

## Welche Seiten zeigen was an?

- `/` (Homepage)
  Einstieg in die drei Dashboards.

- `/fussball`
  Bundesliga Tabelle, Teamauswahl und letzte/nächste Spiele des ausgewählten Teams.

- `/formula1`
  Kommende Rennwochenenden, vergangene Rennwochenenden (on-demand geladen), Session-Ergebnisse und Fahrer-/Team-Championship.

- `/american_football`
  NFL Wochenansicht (Regular Season/Playoffs), Spielscores mit Boxscore-Anreicherung, Team-Roster und Standings (Division/Conference/League).

## Verwendete APIs und Nutzungsregeln

### 1) football-data.org (Fußball)
- Website: https://www.football-data.org/
- Doku: https://docs.football-data.org/
- Im Projekt verwendete Endpunkte:
  - `GET /v4/teams/{team_id}/matches`
  - `GET /v4/competitions/BL1/standings`
- Authentifizierung:
  - Header `X-Auth-Token: <API_KEY>`
- Bekannte Limits laut Doku (Stand 12.04.2026):
  - Free Plan: 10 Requests/Minute für registrierte Clients
  - Details: https://docs.football-data.org/general/v4/policies.html
- Nutzung/Lizenz:
  - Angebote sind planabhängig (free + paid)
  - Bei kommerzieller Nutzung oder höherem Volumen Plan/Vertrag beim Anbieter prüfen

### 2) OpenF1 (Formel 1)
- Website: https://openf1.org/
- Doku: https://openf1.org/docs
- Im Projekt verwendete Endpunkte:
  - `meetings`, `sessions`, `drivers`, `session_result`, `championship_drivers`, `championship_teams`
  - Basis: `https://api.openf1.org/v1`
- Authentifizierung:
  - Für historische Daten kein API Key nötig
- Bekannte Limits laut OpenF1 (Stand der Recherche):
  - Free: bis 3 req/s und 30 req/min
- Wichtiger Lizenz-/Use-Case-Hinweis:
  - OpenF1 beschreibt den Dienst als für persönliche, edukative und nicht-kommerzielle Nutzung
  - Footer/FAQ nennen CC BY-NC-SA 4.0 und non-commercial Fokus
  - Quellen: https://openf1.org/ und https://openf1.org/docs

### 3) Tank01 NFL über RapidAPI (NFL)
- API-Seite: https://rapidapi.com/tank01/api/tank01-nfl-live-in-game-real-time-statistics-nfl
- RapidAPI Terms: https://rapidapi.com/terms
- Im Projekt verwendete Endpunkte:
  - `getNFLTeams`
  - `getNFLGamesForWeek`
  - `getNFLBoxScore`
  - `getNFLTeamRoster`
- Authentifizierung:
  - Header `x-rapidapi-key` und `x-rapidapi-host`
- Nutzung/Lizenz:
  - Plan- und provider-abhängig (RapidAPI Marketplace + API-Provider-Terms)
  - Vor Produktiv- oder kommerzieller Nutzung unbedingt API-spezifische Pricing/Terms prüfen

## Projektstruktur

```text
Sport_Dashboard/
|-- app.py
|-- Procfile
|-- requirements.txt
|-- .env.example
|-- data_sources/
|   |-- get_fussball_data.py
|   |-- get_formula1_data.py
|   `-- get_nfl_data.py
|-- templates/
|   |-- homepage.html
|   |-- fussball.html
|   |-- formula1.html
|   `-- american_football.html
`-- static/
    |-- styles/
    |   `-- sports_dashboard.css
    `-- images/
        |-- BL_Team_Logos/
        |-- F1_Team_Logos/
        |-- NFL_Team_Logos/
        `-- Trophies/
```

## Bugs und Feature Requests

Wenn du einen Bug findest oder ein Feature vorschlagen willst, erstelle bitte ein Issue im Repository:

- Issues: https://github.com/EinfxchNiklas/Sport_Dashboard/issues

Bitte am besten mit:
- kurzer Beschreibung
- Reproduktionsschritten
- erwartetem vs. tatsächlichem Verhalten
- Screenshots/Logs falls hilfreich
