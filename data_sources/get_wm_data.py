"""WM-2026-Daten via OpenLigaDB (Shortcut: wm26, Saison: 2026).

Da die OpenLigaDB-API für WM-Teams kein teamGroupName-Feld befüllt,
werden die Gruppen per Union-Find-Algorithmus aus den Spielpaarungen
rekonstruiert und nach dem Datum des ersten Spiels sortiert (→ A–L).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pytz import timezone as pytz_timezone

from ._openligadb_common import (
    _fetch_competition_group_matches,
    _get_final_result,
    _normalize_icon_url,
    _transform_raw_match,
    _get_cached,
    _set_cached,
)


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

_WM_SHORTCUT = "wm26"
_WM_SEASON = 2026

WM_PHASES = [
    {"orderID": 1, "name": "Gruppenphase Spieltag 1"},
    {"orderID": 2, "name": "Gruppenphase Spieltag 2"},
    {"orderID": 3, "name": "Gruppenphase Spieltag 3"},
    {"orderID": 4, "name": "Sechzehntelfinale"},
    {"orderID": 5, "name": "Achtelfinale"},
    {"orderID": 6, "name": "Viertelfinale"},
    {"orderID": 7, "name": "Halbfinale"},
    {"orderID": 8, "name": "Finale"},
]

_GROUP_LABELS = list("ABCDEFGHIJKL")

_GERMAN_WEEKDAY_FULL = (
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
)


# ---------------------------------------------------------------------------
# Gruppen-Rekonstruktion per Union-Find
# ---------------------------------------------------------------------------

def _reconstruct_groups(all_matches, teams_info):
    """Rekonstruiert WM-Gruppen per Union-Find aus den Gruppenphase-Spielen.

    Da teamGroupName in der API null ist, werden Gruppen anhand der
    Spielpaarungen gebildet: alle Teams, die (direkt oder indirekt)
    gegeneinander gespielt haben, gehören zur selben Gruppe.

    Gibt eine sortierte Liste von Gruppen zurück (Liste von teamId-Listen),
    sortiert nach dem Datum des frühesten Spiels der Gruppe.
    """
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for match in all_matches:
        t1_id = match.get("team1", {}).get("teamId")
        t2_id = match.get("team2", {}).get("teamId")
        if t1_id and t2_id:
            union(t1_id, t2_id)

    groups = {}
    for team_id in teams_info:
        root = find(team_id)
        groups.setdefault(root, []).append(team_id)

    group_list = list(groups.values())

    team_first_match = {}
    for match in sorted(all_matches, key=lambda m: m.get("matchDateTimeUTC", "")):
        for key in ("team1", "team2"):
            tid = match.get(key, {}).get("teamId")
            if tid and tid not in team_first_match:
                team_first_match[tid] = match.get("matchDateTimeUTC", "")

    def group_sort_key(grp):
        dates = [team_first_match.get(t, "") for t in grp]
        valid = [d for d in dates if d]
        return min(valid) if valid else ""

    group_list.sort(key=group_sort_key)
    return group_list


def _build_group_standings(group_team_ids, all_matches, teams_info):
    """Berechnet die Tabelle für eine WM-Gruppe aus allen bisherigen Spielen."""
    standings = {
        tid: {"W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        for tid in group_team_ids
    }

    for match in all_matches:
        t1 = match.get("team1", {})
        t2 = match.get("team2", {})
        t1_id = t1.get("teamId")
        t2_id = t2.get("teamId")
        if t1_id not in standings or t2_id not in standings:
            continue
        if not match.get("matchIsFinished"):
            continue
        final = _get_final_result(match)
        if not final:
            continue

        g1 = final.get("pointsTeam1", 0) or 0
        g2 = final.get("pointsTeam2", 0) or 0
        standings[t1_id]["GF"] += g1
        standings[t1_id]["GA"] += g2
        standings[t2_id]["GF"] += g2
        standings[t2_id]["GA"] += g1

        if g1 > g2:
            standings[t1_id]["W"] += 1
            standings[t1_id]["Pts"] += 3
            standings[t2_id]["L"] += 1
        elif g1 < g2:
            standings[t2_id]["W"] += 1
            standings[t2_id]["Pts"] += 3
            standings[t1_id]["L"] += 1
        else:
            standings[t1_id]["D"] += 1
            standings[t1_id]["Pts"] += 1
            standings[t2_id]["D"] += 1
            standings[t2_id]["Pts"] += 1

    sorted_teams = sorted(
        group_team_ids,
        key=lambda tid: (
            -standings[tid]["Pts"],
            -(standings[tid]["GF"] - standings[tid]["GA"]),
            -standings[tid]["GF"],
            teams_info.get(tid, {}).get("teamName", ""),
        ),
    )

    result = []
    for i, tid in enumerate(sorted_teams):
        s = standings[tid]
        t = teams_info.get(tid, {})
        result.append({
            "position": i + 1,
            "teamId": tid,
            "teamName": t.get("teamName", ""),
            "logo": _normalize_icon_url(t.get("teamIconUrl")),
            "played": s["W"] + s["D"] + s["L"],
            "won": s["W"],
            "drawn": s["D"],
            "lost": s["L"],
            "goalsFor": s["GF"],
            "goalsAgainst": s["GA"],
            "goalDiff": s["GF"] - s["GA"],
            "points": s["Pts"],
        })
    return result


# ---------------------------------------------------------------------------
# Chronologische Match-Liste
# ---------------------------------------------------------------------------

def _build_chronological(current_matches, team_group_label, local_tz):
    """Reichert die Spiele der aktuellen Runde mit Gruppen-Label und
    Datums-Infos an, damit sie chronologisch (nach Anstoßzeit) und nach
    Tagen gruppiert dargestellt werden können.
    """
    today = datetime.now(local_tz).date()
    result = []
    for m in current_matches:
        label = (
            team_group_label.get(m["team1"]["teamId"])
            or team_group_label.get(m["team2"]["teamId"], "")
        )
        match_date = m["matchDate"]
        weekday = _GERMAN_WEEKDAY_FULL[match_date.weekday()]
        date_header = f"{weekday}, {match_date.strftime('%d.%m.%Y')}".upper()
        local_dt = datetime.fromisoformat(m["matchDateTimeUTC"]).astimezone(local_tz)

        entry = dict(m)
        entry["group"] = label
        entry["dateHeader"] = date_header
        entry["timeShort"] = local_dt.strftime("%H:%M")
        entry["isToday"] = match_date == today
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def fetch_wm_data(phase_order_id=1):
    """Gibt WM-2026-Daten für eine Phase zurück.

    Args:
        phase_order_id:
            1–3 → Gruppenphase (Runde 1–3)
            4–8 → K.o.-Phase (Sechzehntelfinale … Finale)

    Returns:
        Dict mit:
            phases           – Liste aller Phasen
            current_phase_id
            is_group_phase   – True wenn Gruppenphase
            groups           – (nur Gruppenphase) Liste von Gruppen-Dicts:
                               {label, standings, matches}
            matches          – (nur K.o.) Spiele der Runde
    """
    local_tz = pytz_timezone("Europe/Berlin")
    cache_key = f"wm_{phase_order_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    is_group_phase = phase_order_id <= 3

    if is_group_phase:
        # Alle 3 Gruppenrunden parallel fetchen (für Standings + Gruppen-Rekonstruktion)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                i: executor.submit(
                    _fetch_competition_group_matches, _WM_SHORTCUT, _WM_SEASON, i
                )
                for i in (1, 2, 3)
            }
            all_raw = {i: f.result() for i, f in futures.items()}

        teams_info = {}
        all_raw_combined = []
        for raw_list in all_raw.values():
            for m in raw_list:
                for key in ("team1", "team2"):
                    t = m.get(key, {})
                    if t.get("teamId"):
                        teams_info[t["teamId"]] = t
            all_raw_combined.extend(raw_list)

        current_raw = all_raw.get(phase_order_id, [])
        current_matches = [
            m for m in [_transform_raw_match(r, local_tz) for r in current_raw] if m
        ]
        current_matches.sort(key=lambda m: m["matchDateTimeUTC"])

        group_team_id_lists = _reconstruct_groups(all_raw_combined, teams_info)

        groups = []
        team_group_label = {}
        for i, team_ids in enumerate(group_team_id_lists):
            label = _GROUP_LABELS[i] if i < len(_GROUP_LABELS) else str(i + 1)
            for tid in team_ids:
                team_group_label[tid] = label
            standings = _build_group_standings(team_ids, all_raw_combined, teams_info)
            group_matches = [
                m for m in current_matches
                if m["team1"]["teamId"] in team_ids
                and m["team2"]["teamId"] in team_ids
            ]
            groups.append({"label": label, "standings": standings, "matches": group_matches})

        chronological_matches = _build_chronological(
            current_matches, team_group_label, local_tz
        )

        result = {
            "phases": WM_PHASES,
            "current_phase_id": phase_order_id,
            "is_group_phase": True,
            "groups": groups,
            "chronological_matches": chronological_matches,
            "matches": [],
        }
    else:
        raw = _fetch_competition_group_matches(_WM_SHORTCUT, _WM_SEASON, phase_order_id)
        matches = [m for m in [_transform_raw_match(r, local_tz) for r in raw] if m]
        matches.sort(key=lambda m: m["matchDateTimeUTC"])

        result = {
            "phases": WM_PHASES,
            "current_phase_id": phase_order_id,
            "is_group_phase": False,
            "groups": [],
            "chronological_matches": [],
            "matches": matches,
        }

    _set_cached(cache_key, result)
    return result
