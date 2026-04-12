# Sport Dashboard

Ein Flask-basiertes Dashboard fuer drei Sportbereiche:
- Fussball (Bundesliga Tabelle + Teamspiele)
- Formel 1 (Rennwochenenden + Session-Ergebnisse + Championship)
- NFL (Wochen-Spiele, Standings, Team-Roster)

## Lokales Setup

### 1. Voraussetzungen
- Python 3.10+ (empfohlen)
- `pip`
- Internetzugang fuer API-Calls

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

### 4. Abhaengigkeiten installieren
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

## Benoetigte Umgebungsvariablen

- `FOOTBALL_DATA_API_KEY`:
  API Key fuer football-data.org (Fussballseite)
- `TANK01_NFL_API_KEY`:
  API Key fuer Tank01 NFL ueber RapidAPI
- `TANK01_NFL_API_KEY_2` (optional):
  Zweiter Key fuer Key-Rotation bei Rate-Limits
- `DEBUG` (optional):
  Flask Debug-Modus (`True`/`False`)
- `PORT` (optional):
  Server-Port (Default: `5000`)

## Welche Seiten zeigen was an?

- `/` (Homepage)
  Einstieg in die drei Dashboards.

- `/fussball`
  Bundesliga Tabelle, Teamauswahl und letzte/naechste Spiele des ausgewaehlten Teams.

- `/formula1`
  Kommende Rennwochenenden, vergangene Rennwochenenden (on-demand geladen), Session-Ergebnisse und Fahrer-/Team-Championship.

- `/american_football`
  NFL Wochenansicht (Regular Season/Playoffs), Spielscores mit Boxscore-Anreicherung, Team-Roster und Standings (Division/Conference/League).

## Verwendete APIs und Nutzungsregeln

Wichtig: API-Anbieter koennen Regeln aendern. Pruefe die verlinkten Seiten regelmaessig.

### 1) football-data.org (Fussball)
- Website: https://www.football-data.org/
- Doku: https://docs.football-data.org/
- Im Projekt verwendete Endpunkte:
  - `GET /v4/teams/{team_id}/matches`
  - `GET /v4/competitions/BL1/standings`
- Authentifizierung:
  - Header `X-Auth-Token: <API_KEY>`
- Bekannte Limits laut Doku (Stand der Recherche):
  - Free Plan: 10 Requests/Minute fuer registrierte Clients
  - Details: https://docs.football-data.org/general/v4/policies.html
- Nutzung/Lizenz:
  - Angebote sind planabhaengig (free + paid)
  - Bei kommerzieller Nutzung oder hoeherem Volumen Plan/Vertrag beim Anbieter pruefen

### 2) OpenF1 (Formel 1)
- Website: https://openf1.org/
- Doku: https://openf1.org/docs
- Im Projekt verwendete Endpunkte:
  - `meetings`, `sessions`, `drivers`, `session_result`, `championship_drivers`, `championship_teams`
  - Basis: `https://api.openf1.org/v1`
- Authentifizierung:
  - Fuer historische Daten kein API Key noetig
- Bekannte Limits laut OpenF1 (Stand der Recherche):
  - Free: bis 3 req/s und 30 req/min
- Wichtiger Lizenz-/Use-Case-Hinweis:
  - OpenF1 beschreibt den Dienst als fuer persoenliche, edukative und nicht-kommerzielle Nutzung
  - Footer/FAQ nennen CC BY-NC-SA 4.0 und non-commercial Fokus
  - Quellen: https://openf1.org/ und https://openf1.org/docs
  - Fuer kommerzielle Nutzung OpenF1 direkt kontaktieren: https://openf1.org/contact

### 3) Tank01 NFL ueber RapidAPI (NFL)
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
  - Plan- und provider-abhaengig (RapidAPI Marketplace + API-Provider-Terms)
  - Vor Produktiv- oder kommerzieller Nutzung unbedingt API-spezifische Pricing/Terms pruefen

## Compliance-Hinweise

- API-Keys niemals committen (`.env` ist bereits in `.gitignore`).
- Bei oeffentlicher Nutzung Impressum/Disclaimer ergaenzen, dass es ein inoffizielles Fanprojekt ist.
- Markenrechte (z. B. F1/NFL/Clublogos) beachten.
- Bei Datenweitergabe oder Monetarisierung immer die aktuell gueltigen API-TOS/Lizenzen vorab juristisch pruefen.

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
- erwartetem vs. tatsaechlichem Verhalten
- Screenshots/Logs falls hilfreich

## Lizenzierung: Wie verhindern, dass andere deinen Code fuer Geld nutzen?

Kurzfassung: Wenn du den Code oeffentlich auf GitHub stellst, kannst du Missbrauch reduzieren, aber nie technisch zu 100% verhindern.

### Option A (empfohlen fuer maximalen Schutz): Proprietary / All Rights Reserved
- Keine Open-Source-Lizenz verwenden.
- Eigenes `LICENSE` mit "All rights reserved" hinterlegen.
- Klarstellen, dass Nutzung, Aenderung, Weitergabe und kommerzielle Verwendung ohne schriftliche Erlaubnis verboten sind.
- Optional: Repo privat halten (staerkster praktischer Schutz).

### Option B: Source-available mit Non-Commercial Klausel
- Z. B. PolyForm Noncommercial (fuer Software besser geeignet als CC-Lizenzen).
- Erlaubt Einsicht/ggf. eingeschraenkte Nutzung, verbietet aber kommerzielle Nutzung.

### Wichtiger Zusatz fuer dieses Projekt
- Durch OpenF1-Daten (non-commercial Fokus laut deren Angaben) ist eine kommerzielle Nutzung deines Gesamtprojekts zusaetzlich kritisch.
- Wenn du spaeter monetarisieren willst, zuerst API-Anbieter-Lizenzen/Vertraege klaeren.

Hinweis: Das ist keine Rechtsberatung. Fuer rechtssichere Produktiv- oder Business-Nutzung sollte ein Jurist die finale Lizenz- und API-Compliance pruefen.
