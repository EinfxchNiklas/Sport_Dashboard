# Sport Dashboard – Frontend Style Guide

> Dieses Dokument beschreibt alle Design-Entscheidungen, Komponenten und Code-Konventionen des Frontends.

---

## Inhaltsverzeichnis

1. [Architektur & Scoping](#1-architektur--scoping)
2. [Farben](#2-farben)
3. [Typografie](#3-typografie)
4. [Layout & Grid](#4-layout--grid)
5. [Buttons](#5-buttons)
6. [Panels & Karten](#6-panels--karten)
7. [Tabellen](#7-tabellen)
8. [Navigation & Tabs](#8-navigation--tabs)
9. [Logos & Bilder](#9-logos--bilder)
10. [Status-Zustände & Feedback](#10-status-zustände--feedback)
11. [Footer](#11-footer)
12. [Mobile / Responsive](#12-mobile--responsive)
13. [Animationen & Transitions](#13-animationen--transitions)
14. [Seitenspezifische Besonderheiten](#14-seitenspezifische-besonderheiten)

---

## 1. Architektur & Scoping

### CSS-Dateien

| Datei | Zweck |
|---|---|
| `static/styles/sports_dashboard.css` | Alle Stile, gegliedert nach Seite |
| `static/styles/sports_dashboard.mobile.css` | Mobile Overrides; muss **nach** der Haupt-CSS geladen werden |

### Page-Scoping-Konvention

Jede Seite bekommt eine eigene Klasse auf `<body>`. Alle CSS-Regeln werden darunter geschachtelt – es gibt **keine globalen, ungescopten Regeln**. Das verhindert Kollisionen zwischen Seiten.

| Seite | Body-Klasse |
|---|---|
| Startseite | `body.page-home` |
| NFL / American Football | `body.page-american` |
| Formel 1 | `body.page-formula1` |
| Fußball / Bundesliga | `body.page-fussball` |
| Dokumentation | `body.page-docs` |
| Impressum / Datenschutz | `body.page-impressum` |

**HTML-Grundgerüst jeder Seite:**

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seitentitel</title>
    <link rel="icon" href="{{ url_for('static', filename='images/favicon.svg') }}" type="image/svg+xml">
    <link rel="stylesheet" href="/static/styles/sports_dashboard.css">
    <link rel="stylesheet" href="/static/styles/sports_dashboard.mobile.css">
</head>
<body class="page-[seitenname]">
    <!-- Inhalt -->
</body>
</html>
```

**CSS-Struktur-Konvention:**

```css
/* Kein unkontrollierter globaler Stil – immer scopen: */
body.page-american .meine-komponente {
    /* Stil */
}
body.page-american .meine-komponente:hover {
    /* Hover-Stil */
}
```

---

## 2. Farben

### Globale Basis (Dark Theme)

| Token | Hex | Verwendung |
|---|---|---|
| Hintergrund | `#141414` | `body`-Hintergrund aller Sport-Seiten |
| Panel | `#1e1e1e` | Karten, Sidebars, Buttons |
| Panel hover | `#2a2a2a` | Hover-Zustand von Panels/Buttons |
| Panel-Header | `#2a2a2a` | Tabellenkopf, Panel-Header-Bereich |
| Trennlinie | `#2d2d2d` | Borders, Trennstriche |
| Text (primary) | `#f5f5f5` | Haupttext auf dunklem Grund |
| Text (sekundär) | `#b0b0b0` / `#9ca3af` | Metadaten, Zeitangaben, Untertitel |
| Text (muted) | `#bdbdbd` | Tabellenkopf-Labels |

### Sport-Akzentfarben

Jede Sportart hat genau **eine Primär-Akzentfarbe**, die für aktive Zustände, Hover-Highlights, Links und Überschriften verwendet wird.

| Sportart | Akzentfarbe | Hex |
|---|---|---|
| NFL / American Football | Grün | `#22c55e` |
| Formel 1 | Rot | `#ff2d2d` |
| Fußball / Bundesliga | Gold | `#ffd24a` |
| Docs / Impressum (H2) | Grün | `#22c55e` |
| Docs / Impressum (Links, H3) | Blau | `#3b82f6` |

### Highlight-Farben (seitenübergreifend)

| Verwendung | Farbe |
|---|---|
| Spielstand / Punkte | `#ffd24a` (Gold) |
| Prozent-Werte (NFL) | `#ffd24a` (Gold) |
| Spieler-Nummer (NFL) | `#ffd24a` (Gold) |

### Bundesliga-Tabellenzeilen (Fußball)

```css
/* Champions League – Ränge 1–4 */
tr.champions-league  { background-color: rgba(30, 80, 200, 0.22); }

/* Europa League – Rang 5 */
tr.europa-league     { background-color: rgba(200, 100, 0, 0.22); }

/* Conference League – Rang 6 */
tr.conference-league { background-color: rgba(30, 150, 60, 0.22); }

/* Relegations-Playoff – Rang 16 */
tr.relegation-playoff { background-color: rgba(200, 50, 50, 0.18); }

/* Abstieg – Ränge 17–18 */
tr.relegation        { background-color: rgba(180, 30, 30, 0.30); }
```

### CSS Custom Properties – Formel 1

Die Formel-1-Seite verwendet CSS-Variablen für konsistentes Theming:

```css
body.page-formula1 {
    --bg:          #121418;
    --panel:       #1e1e1e;
    --panel-open:  #222a35;  /* geöffnetes Weekend-Panel */
    --line:        #2d2d2d;
    --text:        #f4f7fb;
    --muted:       #aeb8c7;
    --accent:      #ff2d2d;
    --accent-soft: rgba(255, 45, 45, 0.16);
}
```

---

## 3. Typografie

### Schriftfamilie

```css
font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
```

Gilt für alle Sport-Seiten. Buttons und Inputs erben mit `font-family: inherit`.

Die Homepage (`body.page-home`) verwendet `Arial, sans-serif` (abweichend, da keine Segoe UI Elemente nötig).

### Überschriftensystem

| Element | Größe | Gewicht | Besonderheit |
|---|---|---|---|
| `h1` (Sport-Seiten) | `clamp(2rem, 3.2vw, 2.5rem)` | 700 | Fluid, linksbündig |
| `h2` (Sektionen) | 20px | variiert | Mit `border-bottom: 2px solid #2d2d2d` |
| `h2` (Docs) | 1.8rem | – | Farbe `#22c55e`, Unterstrich mit 30% Opacity |
| `h3` (Standings) | 14px | – | Background `#262626`, Padding `8px 12px` |
| Panel-Header | 12px | 600 | `text-transform: uppercase; letter-spacing: 0.04em` |

**Fluid H1 (wird auf allen Sport-Seiten einheitlich so gesetzt):**

```css
h1 {
    font-size: clamp(2rem, 3.2vw, 2.5rem);
    font-weight: 700;
    line-height: 1.2;
    text-align: left;
    max-width: 1500px;
    margin: 8px auto 6px auto;
}
```

### Text-Utilities

```css
/* Tabellen-Labels, Panel-Titel */
text-transform: uppercase;
letter-spacing: 0.04em;
font-size: 11px; /* oder 12px */
color: #bdbdbd;

/* Zeiten, monospaced Lap-Times (F1) */
font-family: "Consolas", "Courier New", monospace;
font-variant-numeric: tabular-nums;
```

---

## 4. Layout & Grid

### Max-Width-Regeln

| Seite | Max-Width |
|---|---|
| NFL / Fußball | `1500px` |
| Formel 1 | `1100px` |
| Docs | `1000px` |
| Impressum / Datenschutz | `800px` (Inhaltsbereiche) |

### Sport-Seiten – 3-Spalten-Grid (Desktop)

**NFL:**

```css
body.page-american .page-grid {
    display: grid;
    grid-template-columns: 250px 1fr 400px;
    grid-template-areas: "teams matches standings";
    column-gap: 30px;
    row-gap: 20px;
    align-items: start;
}
```

**Fußball:**

```css
body.page-fussball .page-grid {
    max-width: 1500px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 200px 1fr 360px;
    grid-template-areas: "teams matches standings";
    column-gap: 30px;
    row-gap: 20px;
    align-items: start;
}
```

**Formel 1:**

```css
body.page-formula1 .content-grid {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 16px;
    align-items: start;
}
```

### Page-Padding

```css
body.page-american,
body.page-fussball {
    padding: 30px;
}

body.page-formula1 {
    padding: 24px;
    box-sizing: border-box;
}
```

---

## 5. Buttons

### Home-Button (oben links, fest positioniert)

Auf jeder Unterseite erscheint oben links ein zurück zur Startseite-Button.

```html
<a href="/" class="home-button">← Home</a>
```

```css
/* Sport-Seiten (NFL, Fußball, Formel 1) */
.home-button {
    position: fixed;
    top: 18px;
    left: 18px;
    z-index: 1000;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #f5f5f5;
    text-decoration: none;
    font-size: 13px;
    font-weight: 600;
}
.home-button:hover {
    background: #2a2a2a;
    border-color: [Akzentfarbe];  /* grün / rot / gold je nach Seite */
    color: [Akzentfarbe];
}
```

```css
/* Docs / Impressum – Glasmorphismus-Variante */
.home-button {
    position: fixed;
    top: 24px;
    left: 24px;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 600;
    transition: all 0.3s ease;
}
.home-button:hover {
    border-color: #ffffff;
}
```

---

### Team-Button (.team-btn) – Sidebar-Navigation

Wird in der linken Spalte zur Team-Auswahl verwendet. Enthält ein 24×24-Logo und den Teamnamen.

```html
<!-- Als Link (Fußball) -->
<a href="/fussball?team=5" class="team-btn active">
    <img src="/static/images/..." alt="Bayern München" />
    <span>Bayern München</span>
</a>

<!-- Als Button (NFL) -->
<button type="button" class="team-btn" data-team-id="1">
    <img src="/static/images/..." alt="Kansas City Chiefs" />
    Kansas City Chiefs
</button>
```

```css
.team-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;          /* NFL: 10px 12px | Fußball: 8px 10px */
    background: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #f5f5f5;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s, border-color 0.15s;
    width: 100%;
    box-sizing: border-box;
    text-align: left;
}
.team-btn:hover {
    background: #2a2a2a;
    border-color: #444;
}
.team-btn.active {
    background: #2a2a2a;
    border-color: [Akzentfarbe];  /* #22c55e (NFL) | #ffd24a (Fußball) */
    color: [Akzentfarbe];
    font-weight: 600;
}
.team-btn.disabled {
    cursor: not-allowed;
    opacity: 0.75;
}

/* Logo innerhalb des Buttons */
.team-btn img {
    width: 24px;
    height: 24px;
    min-width: 24px;
    min-height: 24px;
    max-width: 24px;
    max-height: 24px;
    object-fit: contain;
    flex-shrink: 0;
    display: block;
}
```

---

### Wochen/Navigations-Button (.week-btn)

Kleine Pill-Buttons für Spieltag- und Season-Navigation.

```html
<a class="week-btn active" href="/american_football?week=1">Woche 1</a>
<a class="week-btn" href="/american_football?week=2">Woche 2</a>
```

```css
.week-btn {
    padding: 6px 10px;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    text-decoration: none;
    color: #d0d0d0;
    font-size: 12px;
    /* kein Hintergrund */
}
.week-btn:hover,
.week-btn.active {
    border-color: #22c55e;   /* Akzentfarbe der Seite */
    color: #22c55e;
}
.week-btn.active {
    font-weight: 600;
}

/* Saison-Typ-Nav (etwas kleiner) */
.season-type-nav .week-btn {
    padding: 5px 10px;
}
```

---

### Saison-Button (.season-btn-vertical) – Vertikale Liste

```html
<a class="season-btn-vertical active" href="/american_football?season=2024">
    2024<br><span class="current-season-note">(aktuell)</span>
</a>
```

```css
.season-btn-vertical {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 10px 12px;
    background: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #f5f5f5;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s, border-color 0.15s;
    width: 100%;
    box-sizing: border-box;
    text-align: center;
}
.season-btn-vertical:hover  { background: #2a2a2a; border-color: #444; }
.season-btn-vertical.active { background: #2a2a2a; border-color: #22c55e; color: #22c55e; font-weight: 600; }

.current-season-note {
    opacity: 0.6;
    font-size: 11px;
}
```

---

### Filter-Button (.weekend-filter-btn) – Formel 1

Zwei gleichbreite Buttons zum Umschalten zwischen „Upcoming" und „Past Races".

```html
<div class="weekend-filter" data-weekend-filter>
    <button type="button" class="weekend-filter-btn active" data-weekend-target="upcoming">Upcoming Races</button>
    <button type="button" class="weekend-filter-btn" data-weekend-target="past">Past Races</button>
</div>
```

```css
.weekend-filter {
    display: flex;
    width: 100%;
    gap: 8px;
    margin-bottom: 14px;
    max-width: 540px;
}
.weekend-filter-btn {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
    color: var(--text);
    padding: 10px 14px;
    font-size: 0.92rem;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.weekend-filter-btn:hover,
.weekend-filter-btn.active {
    background: var(--panel);
    border-color: var(--accent);  /* #ff2d2d */
    color: var(--accent);
}
```

---

### Compare-Button (.practice-compare-btn) – Formel 1

Sekundärer Ghost-Button zum Aufklappen von Vergleichsansichten.

```html
<button class="practice-compare-btn" type="button">Practice Vergleich</button>
```

```css
.practice-compare-btn {
    display: inline-block;
    padding: 7px 14px;
    background: transparent;
    border: 1px solid #3a4658;
    border-radius: 6px;
    color: #aeb8c7;
    font-size: 0.83rem;
    font-weight: 600;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
}
.practice-compare-btn:hover,
.practice-compare-btn.active {
    border-color: var(--accent);
    color: var(--text);
}
```

---

### Homepage-Buttons (Docs & Impressum) – Glasmorphismus

Fest positionierte Buttons auf der Startseite.

```html
<a href="/docs"      class="docs-button">Docs</a>
<a href="/impressum" class="impressum-button">Impressum</a>
```

```css
.docs-button,
.impressum-button {
    position: fixed;
    bottom: 24px;
    z-index: 999;
    padding: 10px 16px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.3);
    color: rgba(255, 255, 255, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
    letter-spacing: 1px;
}
.docs-button    { right: 24px; }
.impressum-button { left: 24px; }

.docs-button:hover,
.impressum-button:hover {
    background: rgba(255, 255, 255, 0.14);
    color: #ffffff;
    transform: translateY(-2px);
}
```

---

### Roster-Schließen-Button (.roster-close-btn)

Kleiner Ghost-Button zum Schließen von Modal-artigen Panels.

```html
<button class="roster-close-btn" type="button">✕ Schließen</button>
```

```css
.roster-close-btn {
    background: none;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    color: #aaa;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    padding: 6px 12px;
    line-height: 1;
    transition: color 0.15s, border-color 0.15s;
}
.roster-close-btn:hover {
    color: #f5f5f5;
    border-color: #666;
}
```

---

## 6. Panels & Karten

### Standard-Panel

```html
<div class="panel">
    <div class="panel-header">Abschnitt</div>
    <div class="panel-body">
        <!-- Inhalt -->
    </div>
</div>
```

```css
.panel {
    background: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 12px;
    overflow: hidden;
}
.panel-header {
    padding: 12px;
    background: #2a2a2a;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    color: #bdbdbd;
}
.panel-body {
    padding: 8px;
}
.panel-body-vertical {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
```

---

### Rennwochenend-Karte (.weekend) – Formel 1

Aufklappbare Karte. Beim Öffnen wechselt Hintergrund und Border-Farbe.

```html
<article class="weekend" data-weekend>
    <button class="weekend-header" type="button" data-toggle>
        <div>
            <div class="weekend-title">Grand Prix Name</div>
            <div class="weekend-meta">Ort, Land | Start: DD.MM.YYYY</div>
        </div>
    </button>
    <div class="sessions">
        <div class="sessions-inner">
            <div class="session-row">
                <div class="session-name">Qualifying</div>
                <div class="session-time">Sa, 15:00 Uhr</div>
            </div>
        </div>
    </div>
</article>
```

```css
.weekend {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--panel);
    overflow: hidden;
    transition: transform 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}
.weekend:hover           { transform: translateY(-2px); border-color: var(--accent); }
.weekend.open            { background: var(--panel-open); border-color: var(--accent); }
.weekend.open .sessions  { max-height: 3200px; border-color: var(--line); }

.sessions {
    max-height: 0;
    overflow: hidden;
    border-top: 1px solid transparent;
    transition: max-height 0.35s ease, border-color 0.35s ease;
}
```

---

### API-Sperr-Modal (.api-lock-modal) – Fußball

Glasmorphismus-Modal bei Rate-Limit-Überschreitung.

```html
<div class="api-lock-overlay" role="dialog" aria-modal="true" aria-labelledby="apiLockTitle">
    <div class="api-lock-modal">
        <h2 id="apiLockTitle">API-Limit erreicht</h2>
        <p>Beschreibung …</p>
        <div class="api-lock-countdown" id="apiLockCountdown">01:00</div>
        <a class="api-lock-home" href="/">Zur Homepage</a>
    </div>
</div>
```

```css
.api-lock-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    backdrop-filter: blur(4px);
    z-index: 3000;
    padding: 20px;
}
.api-lock-modal {
    width: min(560px, 100%);
    background: rgba(26, 26, 26, 0.8);
    border-radius: 14px;
    backdrop-filter: blur(6px);
    padding: 22px;
    text-align: center;
}
.api-lock-countdown {
    margin: 16px 0 18px;
    font-size: clamp(1.9rem, 5vw, 2.5rem);
    font-weight: 700;
    color: #ffd24a;
    letter-spacing: 0.03em;
}
.api-lock-home {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 44px;
    padding: 10px 16px;
    background: #ffd24a;
    color: #111;
    border-radius: 10px;
    text-decoration: none;
    font-weight: 700;
}
.api-lock-home:hover { background: #f3c52f; }
```

---

### Info-/Warning-Boxen – Docs

```html
<div class="info-box">Hinweis-Text …</div>
<div class="warning-box">Warnung …</div>
```

```css
.info-box {
    background: rgba(34, 197, 94, 0.1);
    border-left: 4px solid #22c55e;
    padding: 15px;
    margin: 20px 0;
    border-radius: 4px;
    color: #d0d0d0;
}
.warning-box {
    background: rgba(239, 68, 68, 0.1);
    border-left: 4px solid #ef4444;
    padding: 15px;
    margin: 20px 0;
    border-radius: 4px;
    color: #d0d0d0;
}
```

---

## 7. Tabellen

### Standard-Tabelle

```html
<table>
    <thead>
        <tr>
            <th>Spalte</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Wert</td>
        </tr>
    </tbody>
</table>
```

```css
table {
    width: 100%;
    border-collapse: collapse;
}
thead {
    background: #2a2a2a;
}
th {
    padding: 12px 14px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 11px;
    color: #bdbdbd;
    font-weight: 600;
}
td {
    padding: 12px 14px;
    border-bottom: 1px solid #2d2d2d;
    font-size: 14px;
}
tbody tr:hover {
    background: #242424;
}
```

> Fußball-Tabellen verwenden etwas größere Padding-Werte (`14px 16px`, `font-size: 15px`).

### Standings-Tabelle (NFL)

```css
.standings-table {
    border-collapse: separate;
    border-spacing: 0;
}
.standings-table th,
.standings-table td {
    padding: 10px 8px;
    font-size: 12px;
    border-bottom: 1px solid #2d2d2d;
}
.pct-value {
    text-align: center;
    color: #ffd24a;
    font-weight: 600;
}
```

### Standings-Abschnitts-Header

```html
<h3 class="standings-header-afc">AFC</h3>
<h3 class="standings-header-nfc">NFC</h3>
```

```css
.standings-section h3 {
    font-size: 14px;
    color: #d9d9d9;
    background: #262626;
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 10px;
}
.standings-header-afc { background: #3d2d2d !important; }  /* Rötlich */
.standings-header-nfc { background: #2d3d4d !important; }  /* Bläulich */
```

### Roster-Tabelle (NFL Modal)

```css
.roster-table {
    font-size: 13px;
    border-collapse: collapse;
}
.roster-table th {
    padding: 7px 10px;
    color: #9ca3af;
    font-size: 11px;
    text-transform: uppercase;
}
.roster-table td {
    padding: 7px 10px;
    border-bottom: 1px solid #222;
    color: #e0e0e0;
}
.roster-table .col-num  { color: #ffd24a; font-weight: 600; text-align: center; }
.roster-table .col-name { font-weight: 600; color: #f5f5f5; }
.roster-table .col-college { color: #9ca3af; font-size: 12px; }
```

---

## 8. Navigation & Tabs

### Spieltag-Navigationsleiste (.week-nav)

```html
<div class="week-nav">
    <a class="week-btn active" href="?week=1">Woche 1</a>
    <a class="week-btn" href="?week=2">Woche 2</a>
</div>
```

```css
.week-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid #2d2d2d;
    background: #1a1a1a;
}
.season-type-nav {
    display: flex;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid #2d2d2d;
}
```

### Inhalts-Tabs (.tabs / .tab-btn)

```html
<div class="tabs">
    <button class="tab-btn active" onclick="showTab('all')">All</button>
    <button class="tab-btn" onclick="showTab('afc')">AFC</button>
</div>
<div class="tab-content active" id="tab-all">…</div>
<div class="tab-content" id="tab-afc">…</div>
```

```css
.tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
    border-bottom: 2px solid #2d2d2d;
}
.tab-btn {
    padding: 10px 16px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: #b0b0b0;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: color 0.2s, border-color 0.2s;
    margin-bottom: -2px;   /* überlappt den .tabs-Border */
}
.tab-btn:hover  { color: #f5f5f5; }
.tab-btn.active { color: #22c55e; border-bottom-color: #22c55e; }

.tab-content        { display: none; }
.tab-content.active { display: block; }
```

### Championship-Switch (Formel 1)

Gleiches Prinzip wie `.tabs`, verwendet Akzentfarbe Rot:

```css
.champ-switch {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
    border-bottom: 2px solid var(--line);
}
.champ-switch-btn {
    padding: 10px 16px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--muted);
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: color 0.2s, border-color 0.2s;
}
.champ-switch-btn:hover  { color: var(--text); }
.champ-switch-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
```

### Mobile Content-Tabs

Nur auf kleinen Bildschirmen sichtbar – schalten zwischen Hauptbereichen:

```html
<div class="mobile-content-tabs">
    <button type="button" class="active" onclick="switchMobileTab(event, 'matches')">Spiele</button>
    <button type="button" onclick="switchMobileTab(event, 'standings')">Standings</button>
</div>
```

### Aufklappbare Sektionen (.mobile-collapsible)

Auf Desktop unsichtbar (Summary ausgeblendet), auf Mobile als `<details>` mit `<summary>` sichtbar.

```html
<details class="mobile-collapsible" data-mobile-collapse-key="american-teams" open>
    <summary>Team-Auswahl</summary>
    <div class="team-picker panel">
        <!-- Inhalt -->
    </div>
</details>
```

```css
/* Desktop: Summary verstecken, kein Rahmen */
.mobile-collapsible         { margin: 0; border: none; }
.mobile-collapsible > summary { display: none; }

/* Mobile: Summary anzeigen */
@media (max-width: 700px) {
    .mobile-collapsible {
        border: 1px solid #2d2d2d;
        border-radius: 10px;
        background: #1b1b1b;
        overflow: hidden;
    }
    .mobile-collapsible > summary {
        display: block;
        cursor: pointer;
        padding: 10px 12px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #d0d0d0;
        background: #252525;
    }
    .mobile-collapsible > summary::after         { content: "Anzeigen"; float: right; color: #9ca3af; }
    .mobile-collapsible[open] > summary::after   { content: "Ausblenden"; }
}
```

---

## 9. Logos & Bilder

### Größen-Standard

| Kontext | Größe | CSS |
|---|---|---|
| Match-Ansicht (NFL) | 50×50px | `width: 50px; height: 50px; object-fit: contain` |
| Sidebar / Team-Picker | 24×24px | `width: 24px; height: 24px; object-fit: contain` |
| Standings-Tabelle (Fußball) | 26×26px | `width: 26px; height: 26px` |
| F1 Championship-Tabelle | 22×22px | `width: 22px; height: 22px` |
| F1 Session-Ergebnis Mini | 16×16px | `width: 16px; height: 16px` |
| Roster-Header (NFL) | 22×22px | `width: 22px; height: 22px` |

### Logo-Regeln

- Immer `object-fit: contain` – kein Zuschneiden
- Immer `flex-shrink: 0` innerhalb von Flex-Containern
- `display: block` verhindern von Inline-Lücken

```css
/* Standard Match-Logo */
.team-logo {
    width: 50px;
    height: 50px;
    min-width: 50px;
    min-height: 50px;
    max-width: 50px;
    max-height: 50px;
    object-fit: contain;
    flex-shrink: 0;
    align-self: center;
    display: block;
}

/* Fallback wenn kein Logo vorhanden */
.team-logo-fallback {
    width: 50px;
    height: 50px;
    background: #2d2d2d;
    border-radius: 4px;
}

/* F1 Placeholder als Kreis */
.team-logo-placeholder {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #2b3443;
    color: #90a1ba;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    flex-shrink: 0;
}
```

### Bilder-Ordner-Struktur

```
static/images/
├── BL_Team_Logos/      # Bundesliga
├── F1_Team_Logos/      # Formel 1
├── NFL_Team_Logos/     # NFL
└── Trophies/           # Homepage-Hintergrund-Trophäen
    ├── Bundesligaschale1.png
    ├── f1_trophy.png
    └── lombardi.png
```

---

## 10. Status-Zustände & Feedback

### Loading-Chip

Kleiner Pill-Indikator neben einem Titel:

```html
<span class="loading-chip">lädt …</span>
```

```css
.loading-chip {
    display: inline-block;
    margin-left: 10px;
    padding: 3px 8px;
    border: 1px solid #2d2d2d;
    border-radius: 999px;
    font-size: 11px;
    color: #9ca3af;
}
```

### Keine-Daten-Zustand

```html
<div class="no-data">Keine Daten verfügbar.</div>
```

```css
.no-data {
    text-align: center;
    padding: 30px;
    color: #999;
    font-size: 14px;
}
```

### Empty-State (Formel 1)

```html
<div class="empty">Keine zukünftigen Rennwochenenden gefunden.</div>
```

```css
.empty {
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 18px;
    background: var(--panel);
    color: var(--muted);
}
```

### Rate-Limit-Warnung (NFL)

```html
<div class="rate-limit-warning">
    ⚠️ API Rate Limit erreicht. Bitte warte X Sekunden.
</div>
```

```css
.rate-limit-warning {
    background: #3d2d2d;
    border: 1px solid #8b4444;
    color: #ff9999;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-size: 13px;
}
```

---

## 11. Footer

Gemeinsamer Footer für alle Sport-Unterseiten (nicht Homepage).

```html
<footer>
    <p>© 2026 Sport Dashboard | <a href="/impressum">Impressum</a></p>
</footer>
```

```css
/* Gemeinsamer Stil */
body.page-american footer,
body.page-formula1 footer,
body.page-fussball footer {
    margin-top: 42px;
    padding: 18px 24px;
    background: #141414;
    border-top: 0.1px solid #4e4e4e;
    text-align: center;
}

/* NFL und Fußball haben 30px Seitenpadding – Footer muss ausbrechen */
body.page-american footer,
body.page-fussball footer {
    margin-left: -30px;
    margin-right: -30px;
    padding-left: 30px;
    padding-right: 30px;
}

/* F1 hat 24px Seitenpadding */
body.page-formula1 footer {
    margin-left: -24px;
    margin-right: -24px;
}

footer a { color: #f5f5f5; }
footer p { margin: 0; }
```

---

## 12. Mobile / Responsive

### Breakpoints

| Breakpoint | Betroffene Seiten | Anwendung |
|---|---|---|
| `max-width: 700px` | NFL, Fußball | Grid → 1 Spalte, Collapsibles aktiv |
| `max-width: 760px` | Docs, Impressum | Home-Button Stil-Wechsel |

### Mobile-Grid (NFL/Fußball)

```css
@media (max-width: 700px) {
    .page-grid {
        grid-template-columns: 1fr;
        grid-template-areas: "matches" "standings" "teams";
        gap: 14px;
    }
}
```

### Mobile-Logo-Größen (NFL)

```css
@media (max-width: 700px) {
    .team-logo,
    .team-logo-fallback {
        width: 34px;
        height: 34px;
        min-width: 34px;
        min-height: 34px;
        max-width: 34px;
        max-height: 34px;
    }
}
```

### Mobile H1

```css
@media (max-width: 700px) {
    h1 {
        margin-top: 56px;   /* Platz für den fixierten Home-Button */
        margin-bottom: 10px;
    }
}
```

### Mobile Roster-Tabs

```css
@media (max-width: 700px) {
    .roster-tab-btn {
        flex: 1 1 0;
        min-width: 0;
        text-align: center;
        padding: 8px 10px;
        font-size: 12px;
    }
}
```

---

## 13. Animationen & Transitions

### Allgemeine Regel

Transitions sind bewusst **kurz und funktional** – keine aufwändigen Keyframe-Animationen.

| Eigenschaft | Dauer | Easing | Anwendung |
|---|---|---|---|
| Background / Border-Color | `0.15s` | linear | Buttons, Team-Buttons |
| Color | `0.2s` | linear | Tabs, Links |
| Transform (Hover) | `0.22s–0.45s` | `ease` | Weekend-Karten, Homepage |
| Flex (Homepage-Section) | `0.5s` | `cubic-bezier(0.4, 0, 0.2, 1)` | Sport-Auswahl-Bereich |
| Max-Height (Accordion) | `0.35s` | `ease` | Aufklappbare Sessions |
| All (Docs/Impressum Home-Button) | `0.3s` | `ease` | Glasmorphismus-Buttons |

### Homepage – Sport-Section Hover-Effekt

```css
.sport-section {
    transition: flex 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.sport-section:hover { flex: 1.18; }

.content {
    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.sport-section:hover .content {
    transform: scale(1.02) translateY(-2px);
}

/* Subtitle erscheint bei Hover */
.sport-subtitle {
    opacity: 0;
    transform: translateY(12px);
    transition: opacity 0.4s ease 0.05s, transform 0.4s ease 0.05s;
}
.sport-section:hover .sport-subtitle {
    opacity: 1;
    transform: translateY(0);
}

/* Trophäen-Layer */
.trophy-layer {
    opacity: 0.23;
    transition: transform 0.45s ease, opacity 0.45s ease, filter 0.45s ease;
}
.sport-section:hover .trophy-layer {
    opacity: 0.31;
    transform: scale(1.03);
    filter: saturate(1.16) contrast(1.1);
}
```

---

## 14. Seitenspezifische Besonderheiten

### Homepage (.page-home)

- Layout: `height: 100vh; overflow: hidden` – kein Scrollen
- 3 gleich breite Flex-Spalten mit `flex: 1`, Hover `flex: 1.18`
- Hintergrund der Sektionen: `radial-gradient` (Akzentfarbe von oben) + `linear-gradient` (dunkel nach unten)
- Trophäen als absolute, halbdurchsichtige Hintergrundbild-Layer (`opacity: 0.23`, `mix-blend-mode: screen`)

### NFL / American Football (.page-american)

- Score-Anzeige in `#ffd24a` Gold, `font-size: 24px`, `font-weight: 700`
- Quarter-Scores: `font-size: 12px`, Farbe `#b0b0b0`
- Roster als Panel innerhalb der Match-Spalte (kein separates Modal)
- AFC-Header rötlich (`#3d2d2d`), NFC-Header bläulich (`#2d3d4d`)

### Formel 1 (.page-formula1)

- Einzige Seite mit CSS Custom Properties (`var(--accent)` etc.)
- Lap-Times / Qualifying-Zeiten: Monospace-Font (`Consolas`), `tabular-nums`
- Session-Ergebnisse: Grid mit `34px 82px 88px` Spalten
- Quali-Ergebnisse: 5-Spalten-Grid mit Q1/Q2/Q3-Zeiten

### Fußball / Bundesliga (.page-fussball)

- Farbkodierte Tabellenzeilen (Europacup- und Abstiegsplätze, s. Abschnitt 2)
- Größeres Standard-Padding in Tabellen-Cells (`14px 16px`)
- API-Limit-Overlay mit Countdown und Blur-Backdrop
