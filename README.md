# Überblick

Dieses Projekt ist ein privates, nicht-kommerzielles Sport-Dashboard, das Daten aus mehreren externen APIs bündelt.

Ziel ist eine zentrale Übersicht für:

- Fußball (Bundesliga)
- Formel 1
- NFL

## Wichtiger Hinweis zur Nutzung dieses Repositories

Dieses Projekt wird öffentlich bereitgestellt, aber ausschließlich für private, nicht-kommerzielle Nutzung.
Jegliche kommerzielle Verwendung ist ausdrücklich nicht gewünscht.

Zusätzlich gelten die Nutzungsbedingungen der eingebundenen API-Anbieter (siehe unten). Diese Regeln sind zwingend einzuhalten.

## Was zeigt die Seite?

- Fußball: Bundesliga-Tabelle und Spiele eines ausgewählten Teams
- Formel 1: kommende und vergangene Rennwochenenden, Session-Ergebnisse, Championship-Stände
- NFL: Wochenübersicht (Regular Season/Playoffs), Scores, Standings, Team-Roster

## Schnellstart (lokal)

1. Repository klonen

```bash
git clone https://github.com/EinfxchNiklas/Sport_Dashboard.git
cd Sport_Dashboard
```

2. Virtuelle Umgebung erstellen und aktivieren (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

4. Umgebungsvariablen setzen

- `.env.example` nach `.env` kopieren
- API-Keys eintragen

Beispiel:

```env
FOOTBALL_DATA_API_KEY=dein_football_data_key
TANK01_NFL_API_KEY=dein_tank01_key
DEBUG=False
PORT=5000
OPENF1_BASE_URL=SET_Base_URL
```

5. Starten

```bash
python app.py
```

Danach im Browser: http://127.0.0.1:5000

## Healthcheck (UptimeRobot)

Für Monitoring kann der Endpunkt `/health` verwendet werden.

- URL lokal: `http://127.0.0.1:5000/health`
- HTTP `200`: Anwendung erreichbar (`ok` oder `degraded`)
- HTTP `503`: Anwendung/API-Konfiguration fehlerhaft (`down`)

Der Endpunkt prüft bei jedem Aufruf:

- generellen Website-Status (wichtige Routen registriert)
- football-data.org API
- OpenF1 API

Beispielantwort:

```json
{
  "status": "ok",
  "checked_at": "2026-04-21T12:34:56.789Z",
  "website": {
    "status": "ok",
    "route_count": 12,
    "missing_routes": []
  },
  "apis": {
    "football_data": {"status": "ok", "http_status": 200, "latency_ms": 180},
    "openf1": {"status": "ok", "http_status": 200, "latency_ms": 95}
  }
}
```

## API-Abhängigkeiten

Die Funktionalität des Projekts hängt von externen APIs ab. Verfügbarkeit und Datenqualität liegen außerhalb meines Einflussbereichs.

## Verwendete APIs, Lizenz- und Nutzungsregeln

Hinweis: Die folgenden Angaben sind nach bestem Wissen dokumentiert (Stand 12.04.2026). Maßgeblich sind immer die aktuellen Originalbedingungen der Anbieter.

### 1) football-data.org (Fußball)

- Website: https://www.football-data.org/
- Dokumentation: https://docs.football-data.org/
- Verwendete Endpunkte:
  - `GET /v4/teams/{team_id}/matches`
  - `GET /v4/competitions/BL1/standings`
- Authentifizierung: `X-Auth-Token` Header
- Rate Limits laut Doku (Policies):
  - Free Plan: 10 Requests pro Minute für registrierte Clients
  - Quelle: https://docs.football-data.org/general/v4/policies.html

### 2) OpenF1 (Formel 1)

- Website: https://openf1.org/
- Dokumentation: https://openf1.org/docs
- Verwendete Endpunkte:
  - `meetings`, `sessions`, `drivers`, `session_result`, `championship_drivers`, `championship_teams`
- Authentifizierung:
  - Historische Daten ohne API-Key
- Public Limits laut OpenF1-Angaben:
  - Free: bis zu 3 Requests/Sekunde und 30 Requests/Minute
- Lizenz-/Nutzungsregel:
  - OpenF1 kommuniziert einen klaren Fokus auf persönliche, edukative und nicht-kommerzielle Nutzung
  - Für andere Use Cases (insbesondere kommerziell) soll OpenF1 direkt kontaktiert werden
  - Quellen: https://openf1.org/, https://openf1.org/docs, https://openf1.org/contact

### 3) Tank01 NFL über RapidAPI

- API-Seite: https://rapidapi.com/tank01/api/tank01-nfl-live-in-game-real-time-statistics-nfl
- RapidAPI Terms: https://rapidapi.com/terms
- Verwendete Endpunkte:
  - `getNFLTeams`
  - `getNFLGamesForWeek`
  - `getNFLBoxScore`
  - `getNFLTeamRoster`
- Authentifizierung:
  - `x-rapidapi-key` und `x-rapidapi-host` Header
- Nutzungsregel:
  - Die API-Nutzung richtet sich nach RapidAPI- und Provider-spezifischen Bedingungen

## Tech Stack

- Backend: Python (Flask)
- Frontend: HTML, CSS, JavaScript
- APIs: football-data.org, OpenF1, Tank01 (RapidAPI)
- Deployment: Render

## Deployment

Das Projekt ist für das Hosting auf Render vorbereitet.

- Build Command: pip install -r requirements.txt
- Start Command: python app.py
- Environment Variables müssen in Render gesetzt werden

Hinweis: Free-Tier kann zu Schlafzeiten führen.

## Projektstruktur

Die folgende Struktur zeigt die Hauptbestandteile der Anwendung und dient der Orientierung im Code.

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

## Einschränkungen

- Abhängigkeit von externen API-Rate-Limits
- Keine garantierte Echtzeitaktualisierung
- Datenverfügbarkeit abhängig von Drittanbietern

## Bugs und Feature Requests

Für Bugs und Feature-Wünsche bitte ein Issue erstellen:

- https://github.com/EinfxchNiklas/Sport_Dashboard/issues

Bitte am besten mit:

- kurzer Beschreibung
- Reproduktionsschritten
- erwartetem vs. tatsächlichem Verhalten
- Screenshots/Logs falls hilfreich

## Trademark and Logo Notice

This project uses team, league, and event logos exclusively for informational and display purposes.
All trademarks, logos, and names belong to their respective rights holders.
There is no connection, partnership, or sponsorship by these organizations.

## Lizenz

Dieses Projekt ist nicht als Open Source lizenziert.

Alle Rechte vorbehalten. Nutzung, Kopie oder Modifikation nur im Rahmen von ausdrücklich genehmigten Pull Requests.
