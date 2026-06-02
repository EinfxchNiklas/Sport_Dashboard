# Changelog

Alle Daten beziehen sich auf den Zeitpunkt, ab dem das Feature auf dem Branch `main` verfügbar war.

Versionsregel:

- Go-Live startet bei v1.0.
- Einträge vor Go-Live bleiben in v0.x.
- Kleine Änderungen und Bugfixes erhöhen die Minor-Version (v1.1, v1.2, ...).
- Größere Erweiterungen (z. B. neue Sportarten oder neue Competitions) erhöhen die Major-Version (v2.0, v3.0, ...).

## v6.1 - 2026-06-02 - Verletzte Spieler (Bundesliga)

Kurzbeschreibung: Auf der Bundesliga-Seite kann je Verein zwischen Spielen und einer Liste verletzter Spieler umgeschaltet werden. Die Verletzungsdaten (Name, Position, Alter, Art der Verletzung, verletzt seit, verpasste Spiele) werden per Web-Scraping von Transfermarkt bezogen und serverseitig gecached.

## v6.0 - 2026-05-23 - DFB-Pokal, Champions League und WM 2026

Kurzbeschreibung: Internationale Fußball-Wettbewerbe wurden als Features gebündelt integriert und die Turnieransichten für den produktiven Einsatz erweitert.

## v5.1 - 2026-05-18 - NFL-Saisonlogik 2026

Kurzbeschreibung: Default-Saison und Spielstatus-Logik für NFL wurden angepasst, um die Wochenauswahl und Darstellung für 2026 zu stabilisieren.

## v5.0 - 2026-05-14 - Wettbewerbe und Logos ausgebaut

Kurzbeschreibung: Wettbewerbs- und UI-Ausbau mit erweiterten Fußball-Ansichten, lokalen Logos und zusätzlichen Mobile-Anpassungen.

## v4.1 - 2026-05-11 - Migration auf OpenLigaDB abgeschlossen

Kurzbeschreibung: Fußball-Datenquelle wurde auf OpenLigaDB umgestellt; dazu kamen Cache-Verbesserungen und ein verbindlicher Styleguide.

## v4.0 - 2026-05-01 - API-Resilienz Fußball verbessert

Kurzbeschreibung: Health-Check-Strategie wurde vereinfacht und die Fußball-API-Robustheit schrittweise verbessert (inkl. temporärer Proxy-Phase und Rückbau).

## v3.3 - 2026-04-26 - Mobile-Optimierung Phase 1

Kurzbeschreibung: Erste große Mobile-Welle mit strukturellem Styling-Update für die Website sowie gezielten Darstellungsverbesserungen.

## v3.2 - 2026-04-25 - Datenschutz und Monitoring geschliffen

Kurzbeschreibung: Umami-Tracking wurde integriert und durch Datenschutz-Updates sowie Logfilter für den Health-Endpunkt sauber flankiert.

## v3.1 - 2026-04-21 - Docs, Impressum und Footer-Rahmen

Kurzbeschreibung: Dokumentationsseite, Impressum, Kontakt und konsistente Footer-Verlinkungen wurden über die Landingpages hinweg ausgerollt.

## v3.0 - 2026-04-12 - Projektdokumentation professionalisiert

Kurzbeschreibung: README, CONTRIBUTING und LICENSE wurden eingeführt bzw. überarbeitet, um Entwicklung und Mitarbeit klar zu strukturieren.

## v2.0 - 2026-04-11 - NFL-Bereich integriert

Kurzbeschreibung: American-Football-Funktionen mit Team-Logos, Roster, Season-Auswahl und API-Key-Fallback wurden als eigener Bereich etabliert.

## v1.2 - 2026-04-09 - Deployment und Caching verbessert

Kurzbeschreibung: ENV-Konfiguration, Render-Vorbereitung sowie Cache- und API-Limit-Handling wurden eingeführt, um Stabilität und Betrieb zu verbessern.

## v1.1 - 2026-04-07 - Formel-1 Anzeige erweitert

Kurzbeschreibung: F1-Ansichten wurden ausgebaut (z. B. Session-Darstellung und Qualifying-Verbesserungen) und die internationale Ausrichtung verfeinert.

## v1.0 - 2026-04-05 - Fußball-Dashboard live (Go-Live)

Kurzbeschreibung: Fußball-Frontend, Routen und Datenabruf wurden zusammengeführt, sodass die erste vollständige Fußball-Ansicht nutzbar war.

## v0.2 - 2026-02-10 - OpenLigaDB-Basis und App-Neustart

Kurzbeschreibung: Umbau der App-Struktur mit Flask-Basis und Anbindung an OpenLigaDB als neues Fundament für Fußball-Daten.

## v0.1 - 2025-09-08 - Projektstart und Grundgerüst

Kurzbeschreibung: Initialer Projekt-Setup mit erster Struktur, Icons und den ersten Scraper-Bausteinen als Basis für das Dashboard.
