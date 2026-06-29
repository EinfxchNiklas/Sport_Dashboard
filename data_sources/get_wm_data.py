"""WM-2026-Daten via OpenLigaDB (Shortcut: wm26, Saison: 2026).

Da die OpenLigaDB-API für WM-Teams kein teamGroupName-Feld befüllt,
werden die Gruppen per Union-Find-Algorithmus aus den Spielpaarungen
rekonstruiert und nach dem Datum des ersten Spiels sortiert (→ A–L).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
import unicodedata

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

_STREAM_PROVIDERS = {
    "ard": {
        "name": "ARD",
        "logo": "/static/images/Streaming Anbieter/ARD_2019_logo.png",
        "url": "https://www.sportschau.de/fussball/fifa-wm-2026",
    },
    "zdf": {
        "name": "ZDF",
        "logo": "/static/images/Streaming Anbieter/ZDF-Logo.png",
        "url": "https://www.zdf.de/fussball-fifa-wm-highlights-live-livestream-100",
    },
    "magenta": {
        "name": "MagentaTV",
        "logo": "/static/images/Streaming Anbieter/MagentaTV-Logo.png",
        "url": "https://www.magenta.tv/url/tvhubs.t-online.de/v3/ftv-web/UnstructuredGrid/482039",
    },
}

# Quelle: vom User gelieferte finale Liste (harte Zuordnung).
_MANUAL_STREAM_OVERRIDES = {
    ("mexiko", "suedafrika"): {"magenta", "zdf"},
    ("suedkorea", "tschechien"): {"magenta"},
    ("kanada", "bosnien herzegowina"): {"ard", "magenta"},
    ("usa", "paraguay"): {"magenta"},
    ("katar", "schweiz"): {"magenta", "zdf"},
    ("brasilien", "marokko"): {"magenta", "zdf"},
    ("haiti", "schottland"): {"ard", "magenta"},
    ("australien", "tuerkei"): {"magenta"},
    ("deutschland", "curacao"): {"ard", "magenta"},
    ("niederlande", "japan"): {"magenta"},
    ("elfenbeinkueste", "ecuador"): {"ard", "magenta"},
    ("schweden", "tunesien"): {"magenta"},
    ("spanien", "kap verde"): {"ard", "magenta"},
    ("belgien", "aegypten"): {"ard", "magenta"},
    ("saudi arabien", "uruguay"): {"magenta", "zdf"},
    ("iran", "neuseeland"): {"magenta", "zdf"},
    ("frankreich", "senegal"): {"magenta"},
    ("irak", "norwegen"): {"magenta"},
    ("argentinien", "algerien"): {"ard", "magenta"},
    ("oesterreich", "jordanien"): {"magenta", "zdf"},
    ("portugal", "dr kongo"): {"magenta", "zdf"},
    ("england", "kroatien"): {"magenta", "zdf"},
    ("ghana", "panama"): {"magenta"},
    ("usbekistan", "kolumbien"): {"magenta"},
    ("tschechien", "suedafrika"): {"magenta", "zdf"},
    ("schweiz", "bosnien herzegowina"): {"magenta"},
    ("kanada", "katar"): {"magenta", "zdf"},
    ("mexiko", "suedkorea"): {"magenta"},
    ("usa", "australien"): {"ard", "magenta"},
    ("schottland", "marokko"): {"magenta"},
    ("brasilien", "haiti"): {"ard", "magenta"},
    ("tuerkei", "paraguay"): {"magenta"},
    ("niederlande", "schweden"): {"magenta", "zdf"},
    ("deutschland", "elfenbeinkueste"): {"magenta", "zdf"},
    ("ecuador", "curacao"): {"magenta", "zdf"},
    ("tunesien", "japan"): {"magenta"},
    ("spanien", "saudi arabien"): {"magenta"},
    ("belgien", "iran"): {"magenta", "zdf"},
    ("uruguay", "kap verde"): {"ard", "magenta"},
    ("neuseeland", "aegypten"): {"magenta"},
    ("argentinien", "oesterreich"): {"ard", "magenta"},
    ("frankreich", "irak"): {"ard", "magenta"},
    ("norwegen", "senegal"): {"magenta"},
    ("jordanien", "algerien"): {"magenta", "zdf"},
    ("portugal", "usbekistan"): {"ard", "magenta"},
    ("england", "ghana"): {"ard", "magenta"},
    ("panama", "kroatien"): {"magenta"},
    ("kolumbien", "dr kongo"): {"ard", "magenta"},
    ("schweiz", "kanada"): {"ard", "magenta"},
    ("bosnien herzegowina", "katar"): {"magenta"},
    ("schottland", "brasilien"): {"magenta"},
    ("marokko", "haiti"): {"magenta", "zdf"},
    ("tschechien", "mexiko"): {"magenta"},
    ("suedafrika", "suedkorea"): {"magenta"},
    ("ecuador", "deutschland"): {"ard", "magenta"},
    ("curacao", "elfenbeinkueste"): {"magenta"},
    ("tunesien", "niederlande"): {"ard", "magenta"},
    ("japan", "schweden"): {"magenta"},
    ("tuerkei", "usa"): {"magenta"},
    ("paraguay", "australien"): {"ard", "magenta"},
    ("norwegen", "frankreich"): {"magenta", "zdf"},
    ("senegal", "irak"): {"magenta"},
    ("uruguay", "spanien"): {"magenta"},
    ("kap verde", "saudi arabien"): {"ard", "magenta"},
    ("neuseeland", "belgien"): {"magenta"},
    ("aegypten", "iran"): {"magenta"},
    ("panama", "england"): {"magenta"},
    ("kroatien", "ghana"): {"magenta", "zdf"},
    ("kolumbien", "portugal"): {"magenta", "zdf"},
    ("dr kongo", "usbekistan"): {"magenta"},
    ("jordanien", "argentinien"): {"magenta"},
    ("algerien", "oesterreich"): {"magenta", "zdf"},
}

_GERMAN_WEEKDAY_FULL = (
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
)


def _normalize_for_matching(value):
    """Normalisiert Teamnamen/Slugs für robuste Vergleiche."""
    value = (value or "").lower().strip()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "&": " und ",
    }
    for src, target in replacements.items():
        value = value.replace(src, target)
    value = value.replace("-", " ")
    value = re.sub(r"\bund\b", " ", value)
    value = "".join(
        ch for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _manual_stream_override_for_match(match):
    """Manuelle Korrekturen für bestätigte Spiele."""
    t1 = _normalize_for_matching(match["team1"]["teamName"])
    t2 = _normalize_for_matching(match["team2"]["teamName"])
    return _MANUAL_STREAM_OVERRIDES.get((t1, t2))


def _load_hardcoded_stream_mapping(current_matches):
    """Liefert eine rein statische Stream-Zuordnung ohne externe Quellen.

    Standard ist MagentaTV; bekannte Spiele werden per festem Override gesetzt.
    """
    mapping = {
        m["matchId"]: {"magenta"}
        for m in current_matches
        if m.get("matchId")
    }

    for match in current_matches:
        match_id = match.get("matchId")
        if not match_id:
            continue
        manual = _manual_stream_override_for_match(match)
        if manual:
            mapping[match_id] = set(manual)

    return mapping


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
# Phasen-Auswahl
# ---------------------------------------------------------------------------

def _fetch_or_cache_phase_raw(phase_order_id):
    """Ruft die Roh-Spiele einer WM-Phase ab (mit Cache)."""
    cache_key = f"wm_raw_{phase_order_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    raw = _fetch_competition_group_matches(_WM_SHORTCUT, _WM_SEASON, phase_order_id)
    _set_cached(cache_key, raw)
    return raw


def _auto_select_default_phase():
    """Waehlt die erste noch nicht vollstaendig gespielte WM-Phase.

    Eine Phase ohne angesetzte Spiele (z.B. die naechste, noch nicht
    ausgeloste Runde) gilt als aktuelle Phase. Sind alle Phasen beendet,
    wird die letzte Phase (Finale) zurueckgegeben.
    """
    for phase_meta in WM_PHASES:
        phase_id = phase_meta["orderID"]
        raw = _fetch_or_cache_phase_raw(phase_id)
        if not raw:
            return phase_id
        if any(not m.get("matchIsFinished", False) for m in raw):
            return phase_id
    return WM_PHASES[-1]["orderID"]


# ---------------------------------------------------------------------------
# Chronologische Match-Liste
# ---------------------------------------------------------------------------

def _build_chronological(current_matches, team_group_label, local_tz, stream_mapping):
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
        provider_keys = sorted(stream_mapping.get(m.get("matchId"), {"magenta"}))
        entry["streams"] = [_STREAM_PROVIDERS[k] for k in provider_keys if k in _STREAM_PROVIDERS]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def fetch_wm_data(phase_order_id=None):
    """Gibt WM-2026-Daten für eine Phase zurück.

    Args:
        phase_order_id:
            1–3 → Gruppenphase (Runde 1–3)
            4–8 → K.o.-Phase (Sechzehntelfinale … Finale)
            None → automatische Auswahl der aktuellen Phase

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

    if phase_order_id is None:
        phase_order_id = _auto_select_default_phase()

    valid_phase_ids = {p["orderID"] for p in WM_PHASES}
    if phase_order_id not in valid_phase_ids:
        phase_order_id = 1

    cache_key = f"wm_v7_{phase_order_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    is_group_phase = phase_order_id <= 3

    if is_group_phase:
        # Alle 3 Gruppenrunden parallel fetchen (für Standings + Gruppen-Rekonstruktion)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                i: executor.submit(_fetch_or_cache_phase_raw, i)
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

        stream_mapping = _load_hardcoded_stream_mapping(current_matches)
        chronological_matches = _build_chronological(
            current_matches, team_group_label, local_tz, stream_mapping
        )

        result = {
            "phases": WM_PHASES,
            "current_phase_id": phase_order_id,
            "is_group_phase": True,
            "groups": groups,
            "chronological_matches": chronological_matches,
            "matches": [],
            "bracket": None,
        }
    else:
        raw = _fetch_or_cache_phase_raw(phase_order_id)
        matches = [m for m in [_transform_raw_match(r, local_tz) for r in raw] if m]
        matches.sort(key=lambda m: m["matchDateTimeUTC"])

        bracket = _build_bracket(local_tz)

        result = {
            "phases": WM_PHASES,
            "current_phase_id": phase_order_id,
            "is_group_phase": False,
            "groups": [],
            "chronological_matches": [],
            "matches": matches,
            "bracket": bracket,
        }

    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Turnierbaum-Builder (K.o.-Phase)
# ---------------------------------------------------------------------------

def _get_winner(match):
    """Gibt die teamId des Siegers zurück, oder None bei Unentschieden/offen."""
    if not match.get("isFinished"):
        return None
    h = match.get("homeScore")
    a = match.get("awayScore")
    try:
        h, a = int(h), int(a)
    except (TypeError, ValueError):
        return None
    if h > a:
        return match["team1"]["teamId"]
    if a > h:
        return match["team2"]["teamId"]
    return None


def _get_loser(match):
    """Gibt die teamId des Verlierers zurück, oder None."""
    winner = _get_winner(match)
    if winner is None:
        return None
    t1 = match["team1"]["teamId"]
    t2 = match["team2"]["teamId"]
    return t2 if winner == t1 else t1


def _make_placeholder():
    """Erstellt einen leeren Slot mit 'noch offen'-Daten."""
    return {
        "matchId": None,
        "team1": {"teamId": None, "teamName": "noch offen", "logo": None},
        "team2": {"teamId": None, "teamName": "noch offen", "logo": None},
        "homeScore": None,
        "awayScore": None,
        "isFinished": False,
        "winnerTeamId": None,
        "formattedDateTime": None,
        "resultName": "",
    }


def _enrich_match(match):
    """Hängt winnerTeamId an ein transformiertes Match-Dict."""
    enriched = dict(match)
    enriched["winnerTeamId"] = _get_winner(match)
    return enriched


def _build_bracket(local_tz):
    """Baut den vollständigen WM-Turnierbaum (Sechzehntelfinale → Finale).

    Reihenfolge der Runden:
        R32 (16 Spiele, orderID 4) → Achtelfinale (8, id 5) →
        Viertelfinale (4, id 6) → Halbfinale (2, id 7) →
        Finale (1, id 8)

    Logik:
    1. Alle K.o.-Phasen parallel laden und transformieren.
    2. Jede Runde wird nach Anstoßzeit sortiert.
    3. Winner-Matching: Folgespiele werden den beiden Vorspielen zugeordnet,
       deren Sieger die Teams des Folgespiels sind (so wird die echte Topologie
       wiederhergestellt, sobald eine Runde ausgelost ist).
    4. Lücken werden mit _make_placeholder() aufgefüllt.
    5. Das "Spiel um Platz 3" ist das Finale-Spiel, dessen Teams die beiden
       Halbfinal-Verlierer sind – es wird separat zurückgegeben.

    Rückgabe:
        {
          "rounds": [
            {"name": str, "matches": [match_or_placeholder, ...]},
            ...  # 5 Einträge: R32, AF, VF, HF, Finale
          ],
          "third_place": match_or_placeholder,
        }
    """
    # K.o.-Phasen-Metadaten (orderID → Rundenname, Slot-Anzahl)
    ko_phases = [
        {"orderID": 4, "name": "Sechzehntelfinale", "slots": 16},
        {"orderID": 5, "name": "Achtelfinale",       "slots": 8},
        {"orderID": 6, "name": "Viertelfinale",      "slots": 4},
        {"orderID": 7, "name": "Halbfinale",         "slots": 2},
        {"orderID": 8, "name": "Finale",             "slots": 1},
    ]

    # 1. Parallel laden
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            p["orderID"]: executor.submit(_fetch_or_cache_phase_raw, p["orderID"])
            for p in ko_phases
        }
        raw_by_phase = {oid: f.result() for oid, f in futures.items()}

    # 2. Transformieren + sortieren
    # K.o.-Runden nach matchId sortieren (API-Reihenfolge = offizielle Bracket-Seedings),
    # nicht nach Datum – so bleiben die korrekten R32→AF→VF→HF Paarungen erhalten.
    matches_by_phase = {}
    for p in ko_phases:
        oid = p["orderID"]
        transformed = [
            m for m in [_transform_raw_match(r, local_tz) for r in raw_by_phase[oid]] if m
        ]
        transformed.sort(key=lambda m: m.get("matchId") or 0)
        matches_by_phase[oid] = [_enrich_match(m) for m in transformed]

    # 3. Halbfinal-Verlierer für "Spiel um Platz 3" merken
    hf_losers = set()
    for m in matches_by_phase.get(7, []):
        loser_id = _get_loser(m)
        if loser_id:
            hf_losers.add(loser_id)

    # 4. Spiel um Platz 3 aus Finale-Runde herauslösen (hat beide HF-Verlierer)
    finale_raw = matches_by_phase.get(8, [])
    third_place = _make_placeholder()
    final_match = _make_placeholder()

    if len(finale_raw) == 1:
        final_match = finale_raw[0]
    elif len(finale_raw) >= 2:
        for m in finale_raw:
            t1 = m["team1"]["teamId"]
            t2 = m["team2"]["teamId"]
            both_losers = (t1 in hf_losers or t1 is None) and (t2 in hf_losers or t2 is None)
            if hf_losers and both_losers:
                third_place = m
            else:
                final_match = m
        # Fallback wenn keine Verlierer noch ermittelbar
        if third_place["matchId"] is None and final_match["matchId"] is None:
            final_match = finale_raw[0]
            if len(finale_raw) > 1:
                third_place = finale_raw[1]

    # 5. Winner-Matching: Folgespiel den Vorspielen zuordnen
    #    Index-Map pro Phase: teamId → match-Slot-Index (für spätere Nutzung im Template)
    def build_round(phase_oid, slot_count, prev_matches):
        """Gibt eine aufgefüllte Liste von `slot_count` Matches zurück.

        Wenn prev_matches vorhanden, wird per Winner-Matching die Topologie hergestellt:
        Jedes aktuelle Match wird dem Paar Vorspiele zugeordnet, deren Sieger seine Teams sind.
        Falls kein Paar passt (Daten noch nicht verfügbar), werden Platzhalter verwendet.
        """
        current = list(matches_by_phase.get(phase_oid, []))

        # Phase noch nicht ausgelost → alles Platzhalter
        if not current:
            return [_make_placeholder() for _ in range(slot_count)]

        # Ohne vorherige Runde → Reihenfolge nach Anstoßzeit nehmen
        if not prev_matches:
            result = list(current)
            while len(result) < slot_count:
                result.append(_make_placeholder())
            return result[:slot_count]

        # Winner-Matching: Sieger des vorherigen Rundenpaars → aktuelles Match
        assigned = [None] * slot_count
        used_curr = set()

        for slot_idx in range(slot_count):
            prev_a = prev_matches[slot_idx * 2] if slot_idx * 2 < len(prev_matches) else None
            prev_b = prev_matches[slot_idx * 2 + 1] if slot_idx * 2 + 1 < len(prev_matches) else None
            winner_a = prev_a["winnerTeamId"] if prev_a else None
            winner_b = prev_b["winnerTeamId"] if prev_b else None

            best_match = None
            best_score = -1
            for ci, cm in enumerate(current):
                if ci in used_curr:
                    continue
                t1 = cm["team1"]["teamId"]
                t2 = cm["team2"]["teamId"]
                score = 0
                if winner_a and t1 == winner_a:
                    score += 2
                if winner_a and t2 == winner_a:
                    score += 2
                if winner_b and t1 == winner_b:
                    score += 2
                if winner_b and t2 == winner_b:
                    score += 2
                # Partial match: one winner known and found
                if winner_a and winner_a in (t1, t2):
                    score += 1
                if winner_b and winner_b in (t1, t2):
                    score += 1
                if score > best_score:
                    best_score = score
                    best_match = (ci, cm)

            if best_match and best_score > 0:
                used_curr.add(best_match[0])
                assigned[slot_idx] = best_match[1]
            else:
                # Kein Winner-Match möglich → Slot-Index-Reihenfolge fallback
                for ci, cm in enumerate(current):
                    if ci not in used_curr:
                        used_curr.add(ci)
                        assigned[slot_idx] = cm
                        break

        return [m if m else _make_placeholder() for m in assigned]

    # Runden aufbauen
    r32 = build_round(4, 16, [])
    af  = build_round(5, 8,  r32)
    vf  = build_round(6, 4,  af)
    hf  = build_round(7, 2,  vf)
    # Finale-Slot immer genau 1
    finale_round = [final_match]

    rounds = [
        {"name": "Sechzehntelfinale", "matches": r32},
        {"name": "Achtelfinale",      "matches": af},
        {"name": "Viertelfinale",     "matches": vf},
        {"name": "Halbfinale",        "matches": hf},
        {"name": "Finale",            "matches": finale_round},
    ]

    return {"rounds": rounds, "third_place": third_place}
