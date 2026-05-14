"""Champions-League-Daten via OpenLigaDB (Shortcut: ucl).

API-Struktur des "ucl"-Shortcuts:
  Group  1– 8  →  Ligaphase Spieltag 1–8 (je eigene Gruppe)
  Group  9     →  Play-offs
  Group 10–11  →  Achtelfinale Hinspiele / Rückspiele
  Group 12–13  →  Viertelfinale Hinspiele / Rückspiele
  Group 14–15  →  Halbfinale Hinspiele / Rückspiele
  Group 16     →  Finale

UI-Phasen (1–6) werden auf API-Gruppen gemappt, damit Hin- und
Rückspiele einer K.o.-Runde zusammen angezeigt werden.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from pytz import timezone as pytz_timezone

from ._openligadb_common import (
    _current_football_season,
    _fetch_competition_group_matches,
    _normalize_icon_url,
    _transform_raw_match,
    _get_cached,
    _set_cached,
)


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

_CL_SHORTCUT = "ucl"

# UI-Phasen (angezeigt in der Navigationsleiste)
CL_PHASES = [
    {"orderID": 1, "name": "Ligaphase"},
    {"orderID": 2, "name": "Play-offs"},
    {"orderID": 3, "name": "Achtelfinale"},
    {"orderID": 4, "name": "Viertelfinale"},
    {"orderID": 5, "name": "Halbfinale"},
    {"orderID": 6, "name": "Finale"},
]

# Mapping: UI-Phase → OpenLigaDB-Group-OrderIDs
_PHASE_TO_API_GROUPS = {
    1: [1, 2, 3, 4, 5, 6, 7, 8],  # Ligaphase: 8 Spieltage
    2: [9],                         # Play-offs
    3: [10, 11],                    # Achtelfinale Hin + Rück
    4: [12, 13],                    # Viertelfinale Hin + Rück
    5: [14, 15],                    # Halbfinale Hin + Rück
    6: [16],                        # Finale
}

_LIGAPHASE_SPIELTAGE = 8

# Ersatz-Logos für Teams, deren API-URLs defekt/blockiert/ohne Transparenz sind
_CL_LOGO_OVERRIDES = {
    # 404-URLs aus API → korrekte Wikipedia-SVG-Dateien
    "Qarabag FK":         "https://upload.wikimedia.org/wikipedia/en/f/fe/Qaraba%C4%9F_FK_logo.svg",
    "Paphos FC":          "https://upload.wikimedia.org/wikipedia/en/9/9b/Pafos_FC_crest.svg",
    "Eintracht Frankfurt": "https://upload.wikimedia.org/wikipedia/en/7/7e/Eintracht_Frankfurt_crest.svg",
    # JPEG-Logos mit weißem Hintergrund → SVG-Versionen ohne Hintergrund
    "FC Arsenal":         "https://upload.wikimedia.org/wikipedia/en/5/53/Arsenal_FC.svg",
    "FC Liverpool":       "https://upload.wikimedia.org/wikipedia/en/0/0c/Liverpool_FC.svg",
    "Union Saint-Gilloise": "https://upload.wikimedia.org/wikipedia/commons/f/f6/USG.png",
}


def _override_logos(matches, table):
    """Ersetzt bekannte fehlerhafte/unpassende Logo-URLs durch korrekte Alternativen."""
    for m in matches:
        for key in ("team1", "team2"):
            name = m.get(key, {}).get("teamName")
            if name in _CL_LOGO_OVERRIDES:
                m[key]["logo"] = _CL_LOGO_OVERRIDES[name]
    for row in table:
        if row.get("teamName") in _CL_LOGO_OVERRIDES:
            row["logo"] = _CL_LOGO_OVERRIDES[row["teamName"]]


def _compute_cl_table_from_ligaphase(all_raw_spieltage):
    """Berechnet die CL-Tabelle ausschließlich aus den Ligaphase-Spielen (Spieltage 1-8).
    
    Args:
        all_raw_spieltage: Dict {1: [...], 2: [...], ..., 8: [...]} mit Raw-Match-Objekten
    
    Returns:
        Liste von Team-Statistiken, sortiert nach Punkten/Torverhältnis
    """
    from collections import defaultdict
    
    team_stats = defaultdict(lambda: {
        "teamId": None,
        "teamName": "",
        "logo": "",
        "played": 0,
        "won": 0,
        "draw": 0,
        "lost": 0,
        "goalsFor": 0,
        "goalsAgainst": 0,
        "points": 0,
    })
    
    # Durch alle 8 Spieltage iterieren
    for spieltag in range(1, _LIGAPHASE_SPIELTAGE + 1):
        raw_matches = all_raw_spieltage.get(spieltag, [])
        for match in raw_matches:
            # Nur beendete Spiele zählen
            if not match.get("matchIsFinished"):
                continue
            
            results = match.get("matchResults", [])
            if not results:
                continue
            
            # Endergebnis ist das letzte Result-Objekt
            final_result = results[-1]
            
            team1 = match.get("team1", {})
            team2 = match.get("team2", {})
            team1_name = team1.get("teamName", "")
            team2_name = team2.get("teamName", "")
            
            if not team1_name or not team2_name:
                continue
            
            goals1 = final_result.get("pointsTeam1", 0)
            goals2 = final_result.get("pointsTeam2", 0)
            
            # Team 1 initialisieren falls neu
            if team_stats[team1_name]["teamId"] is None:
                team_stats[team1_name]["teamId"] = team1.get("teamId")
                team_stats[team1_name]["teamName"] = team1_name
                team_stats[team1_name]["logo"] = _normalize_icon_url(team1.get("teamIconUrl"))
            
            # Team 2 initialisieren falls neu
            if team_stats[team2_name]["teamId"] is None:
                team_stats[team2_name]["teamId"] = team2.get("teamId")
                team_stats[team2_name]["teamName"] = team2_name
                team_stats[team2_name]["logo"] = _normalize_icon_url(team2.get("teamIconUrl"))
            
            # Statistiken aktualisieren
            team_stats[team1_name]["played"] += 1
            team_stats[team2_name]["played"] += 1
            
            team_stats[team1_name]["goalsFor"] += goals1
            team_stats[team1_name]["goalsAgainst"] += goals2
            team_stats[team2_name]["goalsFor"] += goals2
            team_stats[team2_name]["goalsAgainst"] += goals1
            
            if goals1 > goals2:
                team_stats[team1_name]["won"] += 1
                team_stats[team1_name]["points"] += 3
                team_stats[team2_name]["lost"] += 1
            elif goals1 < goals2:
                team_stats[team2_name]["won"] += 1
                team_stats[team2_name]["points"] += 3
                team_stats[team1_name]["lost"] += 1
            else:
                team_stats[team1_name]["draw"] += 1
                team_stats[team2_name]["draw"] += 1
                team_stats[team1_name]["points"] += 1
                team_stats[team2_name]["points"] += 1
    
    # In Liste umwandeln und Torverhältnis berechnen
    table = []
    for stats in team_stats.values():
        stats["goalDiff"] = stats["goalsFor"] - stats["goalsAgainst"]
        table.append(stats)
    
    # Sortieren: 1. Punkte, 2. Torverhältnis, 3. Tore geschossen, 4. Name
    table.sort(
        key=lambda t: (-t["points"], -t["goalDiff"], -t["goalsFor"], t["teamName"])
    )
    
    # Position hinzufügen
    for idx, team in enumerate(table):
        team["position"] = idx + 1
    
    return table


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def fetch_cl_data(phase_order_id=1, spieltag_idx=None):
    """Gibt Champions-League-Daten für eine Phase zurück.

    Args:
        phase_order_id: 1=Ligaphase, 2=Play-offs, 3=Achtelfinale, ...
        spieltag_idx:   0-basierter Spieltag-Index (0–7) innerhalb der Ligaphase.
                        None → automatisch letzter gespielteer Spieltag.

    Returns:
        Dict mit:
            phases          – Liste aller UI-Phasen
            current_phase_id
            matches         – Spiele des gewählten Spieltags / der K.o.-Runde
            spieltage_count – 8 (immer)
            spieltag_idx    – 0-basierter Index des angezeigten Spieltags
            table           – Ligaphase-Tabelle (nur phase_order_id == 1)
            is_ligaphase    – True wenn Ligaphase
    """
    local_tz = pytz_timezone("Europe/Berlin")
    season = _current_football_season()
    is_ligaphase = (phase_order_id == 1)

    # --- Ligaphase ---
    if is_ligaphase:
        # Alle 8 Spieltage parallel fetchen und gemeinsam cachen
        cache_key_raw = f"cl_{season}_all_spieltage"
        all_raw = _get_cached(cache_key_raw)
        if all_raw is None:
            with ThreadPoolExecutor(max_workers=_LIGAPHASE_SPIELTAGE) as executor:
                futs = {
                    i: executor.submit(
                        _fetch_competition_group_matches, _CL_SHORTCUT, season, i
                    )
                    for i in range(1, _LIGAPHASE_SPIELTAGE + 1)
                }
                all_raw = {i: futs[i].result() for i in range(1, _LIGAPHASE_SPIELTAGE + 1)}
            _set_cached(cache_key_raw, all_raw)

        # Default: letzter Spieltag mit mindestens einem Match in der Vergangenheit
        if spieltag_idx is None:
            now_utc = datetime.now(timezone.utc).isoformat()
            spieltag_idx = 0
            for i in range(1, _LIGAPHASE_SPIELTAGE + 1):
                if any(
                    m.get("matchDateTimeUTC", "9999") <= now_utc
                    for m in all_raw.get(i, [])
                ):
                    spieltag_idx = i - 1  # 0-basiert
        spieltag_idx = max(0, min(spieltag_idx, _LIGAPHASE_SPIELTAGE - 1))

        cache_key = f"cl_{season}_st_{spieltag_idx}"
        cached = _get_cached(cache_key)
        if cached:
            return cached

        raw = all_raw.get(spieltag_idx + 1, [])
        matches = [m for m in [_transform_raw_match(r, local_tz) for r in raw] if m]
        matches.sort(key=lambda m: m["matchDateTimeUTC"])

        # Tabelle nur aus Ligaphase-Spielen (Spieltage 1-8) berechnen
        table = _compute_cl_table_from_ligaphase(all_raw)

        _override_logos(matches, table)
        result = {
            "phases": CL_PHASES,
            "current_phase_id": 1,
            "matches": matches,
            "spieltage_count": _LIGAPHASE_SPIELTAGE,
            "spieltag_idx": spieltag_idx,
            "table": table,
            "is_ligaphase": True,
            "season": season,
        }
        _set_cached(cache_key, result)
        return result

    # --- K.o.-Phasen ---
    cache_key = f"cl_{season}_phase_{phase_order_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    api_groups = _PHASE_TO_API_GROUPS.get(phase_order_id, [])
    all_raw_ko = []
    if api_groups:
        with ThreadPoolExecutor(max_workers=len(api_groups)) as executor:
            futs = [
                executor.submit(
                    _fetch_competition_group_matches, _CL_SHORTCUT, season, g
                )
                for g in api_groups
            ]
            for f in futs:
                all_raw_ko.extend(f.result())

    matches = [m for m in [_transform_raw_match(r, local_tz) for r in all_raw_ko] if m]
    matches.sort(key=lambda m: m["matchDateTimeUTC"])

    _override_logos(matches, [])
    result = {
        "phases": CL_PHASES,
        "current_phase_id": phase_order_id,
        "matches": matches,
        "spieltage_count": _LIGAPHASE_SPIELTAGE,
        "spieltag_idx": 0,
        "table": [],
        "is_ligaphase": False,
        "season": season,
    }
    _set_cached(cache_key, result)
    return result
