import json
import os
from threading import Lock
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


load_dotenv()

OPENF1_BASE_URL = (os.environ.get("OPENF1_BASE_URL") or "").rstrip("/")
BERLIN_TZ = ZoneInfo("Europe/Berlin")

API_CACHE = {}
DEFAULT_CACHE_TTL_SECONDS = 180
MIN_REQUEST_INTERVAL_SECONDS = 0.38
LAST_REQUEST_AT_MONOTONIC = 0.0
PERSISTED_STALE_FALLBACK_SECONDS = 60 * 60 * 24 * 3
ENDPOINT_CACHE_TTL_SECONDS = {
    "meetings": 600,
    "sessions": 300,
    "drivers": 300,
    "session_result": 300,
    "championship_drivers": 180,
    "championship_teams": 180,
}
ENDPOINT_PERSISTED_STALE_MAX_AGE_SECONDS = {
    "meetings": 60 * 60 * 24 * 21,
    "sessions": 60 * 60 * 24 * 7,
    "drivers": 60 * 60 * 24 * 7,
    "session_result": 60 * 60 * 24 * 7,
    "championship_drivers": 60 * 60 * 24 * 7,
    "championship_teams": 60 * 60 * 24 * 7,
}

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_RUNTIME_CACHE_DIR = os.path.join(_PROJECT_ROOT, ".cache")
_OPENF1_LAST_KNOWN_CACHE_FILE = os.path.join(_RUNTIME_CACHE_DIR, "openf1_last_known.json")
_LAST_KNOWN_CACHE_LOCK = Lock()
_LAST_KNOWN_CACHE_LOADED = False
_LAST_KNOWN_API_CACHE = {}

TEAM_LOGO_FILES = {
    "McLaren": "mclaren.png",
    "Ferrari": "ferrari.png",
    "Red Bull Racing": "red_bull_racing.png",
    "Mercedes": "mercedes.png",
    "Aston Martin": "aston_martin.png",
    "Alpine": "alpine.png",
    "Williams": "williams.png",
    "Kick Sauber": "sauber.png",
    "Audi": "audi.png",
    "Cadillac": "cadillac.png",
    "Haas F1 Team": "haas.png",
    "Racing Bulls": "racing_bulls.png",
}


def _get_team_logo_url(team_name):
    if not team_name:
        return None
    logo_file = TEAM_LOGO_FILES.get(team_name)
    if not logo_file:
        return None
    return f"/static/images/F1_Team_Logos/{logo_file}"


def _make_cache_key(endpoint, params):
    serialized_params = json.dumps(params or {}, sort_keys=True, default=str)
    return f"{endpoint}|{serialized_params}"


def _load_last_known_api_cache_once():
    global _LAST_KNOWN_CACHE_LOADED, _LAST_KNOWN_API_CACHE

    if _LAST_KNOWN_CACHE_LOADED:
        return

    with _LAST_KNOWN_CACHE_LOCK:
        if _LAST_KNOWN_CACHE_LOADED:
            return

        try:
            with open(_OPENF1_LAST_KNOWN_CACHE_FILE, "r", encoding="utf-8") as cache_file:
                payload = json.load(cache_file)
                if isinstance(payload, dict):
                    _LAST_KNOWN_API_CACHE = payload
                else:
                    _LAST_KNOWN_API_CACHE = {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            _LAST_KNOWN_API_CACHE = {}

        _LAST_KNOWN_CACHE_LOADED = True


def _persist_last_known_api_cache():
    try:
        os.makedirs(_RUNTIME_CACHE_DIR, exist_ok=True)
        tmp_path = _OPENF1_LAST_KNOWN_CACHE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as cache_file:
            json.dump(_LAST_KNOWN_API_CACHE, cache_file, ensure_ascii=True, separators=(",", ":"))
        os.replace(tmp_path, _OPENF1_LAST_KNOWN_CACHE_FILE)
    except OSError:
        # Ignore disk cache write issues; in-memory cache still works.
        return


def _store_last_known_snapshot(cache_key, data):
    if not isinstance(data, list) or not data:
        return

    _load_last_known_api_cache_once()
    with _LAST_KNOWN_CACHE_LOCK:
        _LAST_KNOWN_API_CACHE[cache_key] = {
            "updated_at": time.time(),
            "data": data,
        }
        _persist_last_known_api_cache()


def _get_last_known_snapshot(cache_key, endpoint):
    _load_last_known_api_cache_once()
    entry = _LAST_KNOWN_API_CACHE.get(cache_key)
    if not isinstance(entry, dict):
        return None

    data = entry.get("data")
    updated_at = entry.get("updated_at")
    if not isinstance(data, list) or not data:
        return None
    if not isinstance(updated_at, (int, float)):
        return None

    max_age_seconds = ENDPOINT_PERSISTED_STALE_MAX_AGE_SECONDS.get(
        endpoint,
        PERSISTED_STALE_FALLBACK_SECONDS,
    )
    age_seconds = time.time() - float(updated_at)
    if age_seconds > max_age_seconds:
        return None

    return data


def _get_best_stale_fallback(cache_key, endpoint, cached_entry):
    if cached_entry and cached_entry.get("data"):
        cached_entry["expires_at"] = time.monotonic() + 60
        return cached_entry["data"]

    persisted_data = _get_last_known_snapshot(cache_key, endpoint)
    if persisted_data:
        API_CACHE[cache_key] = {
            "expires_at": time.monotonic() + 60,
            "data": persisted_data,
        }
        return persisted_data

    return []


def _get_json(endpoint, params=None, retries=3):
    """Performs a GET request with basic retry for transient and rate-limit errors."""
    global LAST_REQUEST_AT_MONOTONIC
    params = params or {}
    cache_key = _make_cache_key(endpoint, params)
    now_monotonic = time.monotonic()
    cached_entry = API_CACHE.get(cache_key)

    if cached_entry and cached_entry["expires_at"] > now_monotonic:
        return cached_entry["data"]

    for attempt in range(max(retries, 5)):
        try:
            # Keep requests below the free-tier OpenF1 limit (3 req/s).
            elapsed = time.monotonic() - LAST_REQUEST_AT_MONOTONIC
            if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
                time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

            resolved_endpoint = str(endpoint).strip("/")
            response = requests.get(
                f"{OPENF1_BASE_URL}/{resolved_endpoint}",
                params=params,
                timeout=15,
            )
            LAST_REQUEST_AT_MONOTONIC = time.monotonic()

            # OpenF1 free tier is rate-limited (3 req/s). Retry with short backoff.
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 1.2
                time.sleep(wait_seconds)
                raise requests.HTTPError("rate_limited", response=response)

            # Do not retry hard client errors like 400/404.
            if 400 <= response.status_code < 500:
                return _get_best_stale_fallback(cache_key, endpoint, cached_entry)

            response.raise_for_status()
            payload = response.json()
            # OpenF1 can return HTTP 200 with non-list payloads (e.g. message text for plan limits).
            # Treat those as unavailable live data and fallback to last known snapshot.
            data = payload if isinstance(payload, list) else []
            ttl = ENDPOINT_CACHE_TTL_SECONDS.get(endpoint, DEFAULT_CACHE_TTL_SECONDS)
            if data:
                # Got real data → cache normally
                API_CACHE[cache_key] = {
                    "expires_at": time.monotonic() + ttl,
                    "data": data,
                }
                _store_last_known_snapshot(cache_key, data)
                return data
            # API returned no list data (e.g. during a live session).
            return _get_best_stale_fallback(cache_key, endpoint, cached_entry)
        except (requests.exceptions.RequestException, ValueError):
            if attempt == max(retries, 5) - 1:
                return _get_best_stale_fallback(cache_key, endpoint, cached_entry)
            time.sleep(0.55 * (attempt + 1))

    return _get_best_stale_fallback(cache_key, endpoint, cached_entry)


def _parse_iso_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_driver_display_name(driver, driver_number=None):
    first_name = driver.get("first_name")
    last_name = driver.get("last_name")
    if first_name and last_name:
        return f"{first_name[0]}. {last_name}"

    broadcast_name = driver.get("broadcast_name")
    if broadcast_name:
        parts = broadcast_name.split()
        if len(parts) >= 2 and parts[0]:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"
        return broadcast_name

    full_name = driver.get("full_name")
    if full_name:
        parts = full_name.split()
        if len(parts) >= 2 and parts[0]:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"
        return full_name

    if driver_number is not None:
        return f"#{driver_number}"

    return "Unknown"


def _format_driver_acronym(driver):
    acronym = driver.get("name_acronym")
    if acronym:
        return acronym.capitalize()

    last_name = driver.get("last_name")
    if last_name:
        return last_name[:3].capitalize()

    full_name = driver.get("full_name")
    if full_name:
        return full_name.split()[-1][:3].capitalize()

    return None


def _format_full_result(result_rows, acronym_by_driver_number=None):
    if not result_rows:
        return None

    ordered_rows = sorted(
        [r for r in result_rows if isinstance(r, dict) and r.get("position") is not None],
        key=lambda r: r.get("position"),
    )
    if not ordered_rows:
        return None

    parts = []
    for row in ordered_rows:
        position = row.get("position")
        driver_number = row.get("driver_number")
        if position is None or driver_number is None:
            continue
        driver_tag = (acronym_by_driver_number or {}).get(driver_number)
        if not driver_tag:
            driver_tag = f"#{driver_number}"
        parts.append(f"P{position} {driver_tag}")

    return " | ".join(parts) if parts else None


def _session_result_title(session_name):
    if session_name == "Race":
        return "Rennergebnis"
    if session_name == "Qualifying":
        return "Qualifying"
    if session_name == "Sprint":
        return "Sprint"
    return "Ergebnis"


def _last_non_null(value):
    if isinstance(value, list):
        for item in reversed(value):
            if item is not None:
                return item
        return None
    return value


def _format_seconds_to_lap_time(seconds_value):
    try:
        duration_float = float(seconds_value)
        minutes = int(duration_float // 60)
        seconds = duration_float % 60
        return f"{minutes}:{seconds:06.3f}"
    except (TypeError, ValueError):
        return None


def _format_interval_to_previous(current_gap, previous_gap):
    try:
        gap_float = float(current_gap)
    except (TypeError, ValueError):
        return None

    if previous_gap is not None:
        try:
            previous_gap_float = float(previous_gap)
            interval_to_previous = gap_float - previous_gap_float
            if interval_to_previous > 0:
                return f"+{interval_to_previous:.3f}s"
        except (TypeError, ValueError):
            pass

    if gap_float > 0:
        return f"+{gap_float:.3f}s"

    return None


def _build_session_result_rows(
    result_rows,
    acronym_by_driver_number=None,
    team_logo_by_driver_number=None,
    session_name=None,
):
    if not result_rows or not isinstance(result_rows, list):
        return []
    
    valid_rows = [r for r in result_rows if isinstance(r, dict) and r.get("driver_number") is not None]

    def _row_sort_key(row):
        position = row.get("position")
        if position is not None:
            return (0, position)
        return (1, row.get("driver_number") or 999)

    ordered_rows = sorted(valid_rows, key=_row_sort_key)

    leader_laps = None
    if ordered_rows:
        leader_laps = ordered_rows[0].get("number_of_laps")

    rows = []
    previous_gap = None
    previous_gap_by_quali_phase = [None, None, None]
    quali_phase_labels = ("Q1", "Q2", "Q3")
    for idx, row in enumerate(ordered_rows):
        position = row.get("position")
        driver_number = row.get("driver_number")
        if driver_number is None:
            continue

        if position is not None:
            position_label = f"P{position}"
        elif row.get("dsq"):
            position_label = "DSQ"
        elif row.get("dns"):
            position_label = "DNS"
        elif row.get("dnf"):
            position_label = "DNF"
        else:
            position_label = "NC"

        # Get gap_to_leader - handle both scalar and array values
        raw_gap = row.get("gap_to_leader")
        current_gap = _last_non_null(raw_gap)

        # Get duration - handle both scalar and array values
        raw_duration = row.get("duration")
        current_duration = _last_non_null(raw_duration)

        # Determine time/gap display based on session type
        time_or_gap = None
        
        is_quali_like = session_name in ("Qualifying", "Sprint Qualifying", "Sprint Shootout")
        time_or_gap_phases = []

        if session_name in ("Race", "Sprint"):
            # For Race/Sprint: Leader shows "Leader", others show gap to previous car
            if idx == 0 and position is not None:
                time_or_gap = "Leader"
            else:
                if current_gap is not None:
                    time_or_gap = _format_interval_to_previous(current_gap, previous_gap)

                if time_or_gap is None and row.get("dnf"):
                    time_or_gap = "-"

                if time_or_gap is None and leader_laps is not None and not row.get("dnf"):
                    current_laps = row.get("number_of_laps")
                    if current_laps is not None:
                        try:
                            lap_diff = int(leader_laps) - int(current_laps)
                            if lap_diff > 0:
                                lap_label = "Lap" if lap_diff == 1 else "Laps"
                                time_or_gap = f"+{lap_diff} {lap_label}"
                        except (TypeError, ValueError):
                            pass
        else:
            # For Qualifying/Practice: First shows best lap time, others show interval to previous
            show_lap_time_for_position = is_quali_like and position in (11, 17)

            if is_quali_like:
                gap_values = raw_gap if isinstance(raw_gap, list) else [raw_gap]
                duration_values = raw_duration if isinstance(raw_duration, list) else [raw_duration]

                for phase_idx, phase_label in enumerate(quali_phase_labels):
                    phase_gap = gap_values[phase_idx] if phase_idx < len(gap_values) else None
                    phase_duration = (
                        duration_values[phase_idx] if phase_idx < len(duration_values) else None
                    )

                    phase_display = _format_interval_to_previous(
                        phase_gap,
                        previous_gap_by_quali_phase[phase_idx],
                    )
                    if phase_display is None and phase_duration is not None:
                        phase_display = _format_seconds_to_lap_time(phase_duration)

                    if phase_display is not None:
                        time_or_gap_phases.append({"label": phase_label, "value": phase_display})

                    if phase_gap is not None:
                        previous_gap_by_quali_phase[phase_idx] = phase_gap

                if time_or_gap_phases:
                    time_or_gap = time_or_gap_phases[-1]["value"]
            elif current_duration is not None and (idx == 0 or show_lap_time_for_position):
                time_or_gap = _format_seconds_to_lap_time(current_duration)
            elif current_gap is not None:
                time_or_gap = _format_interval_to_previous(current_gap, previous_gap)

        rows.append(
            {
                "position": position,
                "position_label": position_label,
                "driver": (acronym_by_driver_number or {}).get(driver_number, f"#{driver_number}"),
                "team_logo": (team_logo_by_driver_number or {}).get(driver_number),
                "time_or_gap": time_or_gap,
                "time_or_gap_phases": time_or_gap_phases,
            }
        )

        if current_gap is not None and not is_quali_like:
            previous_gap = current_gap

    return rows


def _get_session_result_summary(session_name, session_key):
    if not session_key:
        return None

    result_rows = _get_json(
        "session_result",
        params={"session_key": session_key, "position<=": 3},
    )
    if not result_rows:
        return None

    podium_summary = _format_full_result(result_rows)
    if not podium_summary:
        return None

    if session_name == "Race":
        return f"Rennergebnis: {podium_summary}"
    if session_name == "Qualifying":
        return f"Qualifying: {podium_summary}"
    if session_name == "Sprint":
        return f"Sprint: {podium_summary}"
    return f"Ergebnis: {podium_summary}"


def _get_meeting_result_summary_map(
    meeting_key,
    session_name_by_key=None,
    acronym_by_driver_number=None,
):
    if not meeting_key:
        return {}

    result_rows = _get_json(
        "session_result",
        params={"meeting_key": meeting_key},
    )
    if not result_rows:
        return {}

    results_by_session = {}
    for row in result_rows:
        if not isinstance(row, dict):
            continue
        session_key = row.get("session_key")
        if not session_key:
            continue
        results_by_session.setdefault(session_key, []).append(row)

    summary_map = {}
    for session_key, rows in results_by_session.items():
        session_name = (session_name_by_key or {}).get(session_key)
        if not session_name and rows:
            session_name = rows[0].get("session_name")

        podium_summary = _format_full_result(rows, acronym_by_driver_number=acronym_by_driver_number)
        if not podium_summary:
            continue

        if session_name == "Race":
            summary_map[session_key] = f"Rennergebnis: {podium_summary}"
        elif session_name == "Qualifying":
            summary_map[session_key] = f"Qualifying: {podium_summary}"
        elif session_name == "Sprint":
            summary_map[session_key] = f"Sprint: {podium_summary}"
        else:
            summary_map[session_key] = f"Ergebnis: {podium_summary}"

    return summary_map


def fetch_meeting_session_result_summaries(meeting_key):
    """
    Returns a mapping of session_key -> summary text for one meeting.
    Intended for lazy-loading results when a past weekend is expanded.
    """
    sessions_payload = _get_json("sessions", params={"meeting_key": meeting_key})
    drivers_payload = _get_json("drivers", params={"meeting_key": meeting_key})

    session_name_by_key = {}
    for session in sessions_payload:
        if not isinstance(session, dict):
            continue
        session_key = session.get("session_key")
        session_name = session.get("session_name")
        if session_key and session_name:
            session_name_by_key[session_key] = session_name

    acronym_by_driver_number = {}
    team_logo_by_driver_number = {}
    for driver in drivers_payload:
        if not isinstance(driver, dict):
            continue
        driver_number = driver.get("driver_number")
        if not driver_number:
            continue
        acronym = _format_driver_acronym(driver)
        if acronym:
            acronym_by_driver_number[driver_number] = acronym
        team_logo_by_driver_number[driver_number] = _get_team_logo_url(driver.get("team_name"))

    result_rows = _get_json("session_result", params={"meeting_key": meeting_key})
    results_by_session = {}
    for row in result_rows:
        if not isinstance(row, dict):
            continue
        session_key = row.get("session_key")
        if not session_key:
            continue
        results_by_session.setdefault(session_key, []).append(row)

    payload = {}
    for session_key, rows in results_by_session.items():
        session_name = session_name_by_key.get(session_key)
        formatted_rows = _build_session_result_rows(
            rows,
            acronym_by_driver_number=acronym_by_driver_number,
            team_logo_by_driver_number=team_logo_by_driver_number,
            session_name=session_name,
        )
        if not formatted_rows:
            continue

        payload[str(session_key)] = {
            "title": _session_result_title(session_name),
            "session_name": session_name,
            "rows": formatted_rows,
        }

    return payload


def _past_session_sort_key(session):
    session_name = session.get("session_name") or ""
    priority_map = {
        "Race": 0,
        "Sprint": 1,
        "Qualifying": 2,
        "Sprint Qualifying": 3,
        "Practice 3": 4,
        "Practice 2": 5,
        "Practice 1": 6,
    }
    priority = priority_map.get(session_name, 99)
    session_dt = _parse_iso_datetime(session.get("date_start"))
    timestamp = session_dt.timestamp() if session_dt else 0
    return (priority, -timestamp)


def fetch_current_race_weekend():
    """
    Returns the currently active race weekend, or None if no race weekend is active.
    A weekend is considered active when at least one session has started and the
    Race session ended less than 4 hours ago (or hasn't started yet).
    """
    from datetime import timedelta

    now = datetime.now(BERLIN_TZ)
    year = now.year
    meeting_params = {"year": year}
    meetings_payload = _get_json("meetings", params=meeting_params)
    sessions_payload = _get_json("sessions", params=meeting_params)

    if not meetings_payload or not sessions_payload:
        return None

    excluded_meeting_keys = {"1282", "1283"}

    sessions_by_meeting = {}
    for session in sessions_payload:
        meeting_key = session.get("meeting_key")
        if not meeting_key:
            continue
        sessions_by_meeting.setdefault(meeting_key, []).append(session)

    for meeting in sorted(meetings_payload, key=lambda m: m.get("date_start") or ""):
        meeting_key = meeting.get("meeting_key")
        if not meeting_key or str(meeting_key) in excluded_meeting_keys:
            continue

        sessions = sessions_by_meeting.get(meeting_key, [])
        if not sessions:
            continue

        session_starts = [
            _parse_iso_datetime(s.get("date_start"))
            for s in sessions
            if s.get("date_start")
        ]
        if not session_starts:
            continue

        first_session_start = min(session_starts)

        # Find the Race session to determine end of weekend
        race_session_start = None
        for s in sessions:
            if s.get("session_name") == "Race":
                race_session_start = _parse_iso_datetime(s.get("date_start"))
                break

        # Fall back to last session start if no Race session found
        end_anchor = race_session_start if race_session_start else max(session_starts)
        weekend_end = end_anchor + timedelta(hours=4)

        if first_session_start <= now <= weekend_end:
            parsed_sessions = []
            for s in sorted(sessions, key=lambda x: x.get("date_start") or ""):
                start_dt = _parse_iso_datetime(s.get("date_start"))
                parsed_sessions.append({
                    "session_name": s.get("session_name", "Session"),
                    "date_start": s.get("date_start"),
                    "session_key": s.get("session_key"),
                    "formatted_date": start_dt.astimezone(BERLIN_TZ).strftime("%d.%m.%Y") if start_dt else "TBA",
                    "formatted_time": start_dt.astimezone(BERLIN_TZ).strftime("%H:%M") if start_dt else "--:--",
                    "is_past": bool(start_dt and start_dt < now),
                    "is_live": bool(
                        start_dt
                        and start_dt <= now <= start_dt + timedelta(hours=3)
                    ),
                })

            has_practice = any(s.get("session_name", "").startswith("Practice") for s in sessions)
            is_sprint = any("Sprint" in s.get("session_name", "") for s in sessions)

            meeting_start = _parse_iso_datetime(meeting.get("date_start"))
            return {
                "meeting_key": meeting_key,
                "meeting_name": meeting.get("meeting_name", "Grand Prix"),
                "country_name": meeting.get("country_name", "Unknown"),
                "country_code": meeting.get("country_code"),
                "location": meeting.get("location", "Unknown"),
                "year": meeting.get("year"),
                "formatted_weekend": (
                    meeting_start.astimezone(BERLIN_TZ).strftime("%d.%m.%Y")
                    if meeting_start
                    else "TBA"
                ),
                "sessions": parsed_sessions,
                "show_practice_compare": has_practice and not is_sprint,
            }

    return None


def fetch_formula1_weekends(
    limit=12,
    year=None,
    upcoming_only=False,
    timeframe="all",
    include_session_results=False,
):
    """
    Fetches Formula 1 race weekends and session schedules from OpenF1.
    Returns a list of meetings, each including sorted session entries.
    """
    meeting_params = {"year": year if year is not None else datetime.now().year}
    meetings_payload = _get_json("meetings", params=meeting_params)
    sessions_payload = _get_json("sessions", params=meeting_params)

    if not meetings_payload:
        return []

    now = datetime.now(BERLIN_TZ)

    # Filter only the two specific canceled race weekends by meeting_key.
    excluded_meeting_keys = {"1282", "1283"}
    meetings = [
        m
        for m in meetings_payload
        if m.get("meeting_key") and str(m.get("meeting_key")) not in excluded_meeting_keys
    ]

    past_result_summaries_by_meeting = {}

    sessions_by_meeting = {}
    for session in sessions_payload:
        meeting_key = session.get("meeting_key")
        if not meeting_key:
            continue

        start_dt = _parse_iso_datetime(session.get("date_start"))
        is_past_session = bool(start_dt and start_dt < now)
        parsed_session = {
            "session_name": session.get("session_name", "Session"),
            "date_start": session.get("date_start"),
            "session_key": session.get("session_key"),
            "formatted_date": start_dt.astimezone(BERLIN_TZ).strftime("%d.%m.%Y") if start_dt else "TBA",
            "formatted_time": start_dt.astimezone(BERLIN_TZ).strftime("%H:%M") if start_dt else "--:--",
        }

        if include_session_results and is_past_session:
            summary_map = past_result_summaries_by_meeting.get(meeting_key, {})
            parsed_session["result_summary"] = summary_map.get(parsed_session["session_key"])

        sessions_by_meeting.setdefault(meeting_key, []).append(parsed_session)

    for meeting_key in sessions_by_meeting:
        if timeframe == "past":
            sessions_by_meeting[meeting_key].sort(key=_past_session_sort_key)
        else:
            sessions_by_meeting[meeting_key].sort(key=lambda s: s.get("date_start") or "")

    race_weekends = []
    for meeting in meetings:
        meeting_key = meeting.get("meeting_key")
        parsed_sessions = sessions_by_meeting.get(meeting_key, [])

        meeting_start = _parse_iso_datetime(meeting.get("date_start"))
        race_weekends.append(
            {
                "meeting_key": meeting_key,
                "meeting_name": meeting.get("meeting_name", "Grand Prix"),
                "country_name": meeting.get("country_name", "Unknown"),
                "country_code": meeting.get("country_code"),
                "location": meeting.get("location", "Unknown"),
                "year": meeting.get("year"),
                "date_start": meeting.get("date_start"),
                "formatted_weekend": (
                    meeting_start.astimezone(BERLIN_TZ).strftime("%d.%m.%Y")
                    if meeting_start
                    else "TBA"
                ),
                "sessions": parsed_sessions,
            }
        )

    if upcoming_only and timeframe == "all":
        timeframe = "upcoming"

    if timeframe == "upcoming":
        race_weekends = [
            w
            for w in race_weekends
            if _parse_iso_datetime(w.get("date_start")) and _parse_iso_datetime(w.get("date_start")) >= now
        ]
        race_weekends.sort(key=lambda w: w.get("date_start") or "")
    elif timeframe == "past":
        race_weekends = [
            w
            for w in race_weekends
            if _parse_iso_datetime(w.get("date_start")) and _parse_iso_datetime(w.get("date_start")) < now
        ]
        race_weekends.sort(key=lambda w: w.get("date_start") or "", reverse=True)
    else:
        def _weekend_sort_key(weekend):
            start_dt = _parse_iso_datetime(weekend.get("date_start"))
            if not start_dt:
                return (2, float("inf"))

            timestamp = start_dt.timestamp()
            if start_dt >= now:
                return (0, timestamp)

            return (1, -timestamp)

        race_weekends.sort(key=_weekend_sort_key)

    if limit is not None:
        return race_weekends[:limit]

    return race_weekends


def fetch_championship_standings(year=None):
    """
    Fetches the latest available driver and constructor championship standings.
    Returns data for one race session to keep both tables in sync.
    """
    target_year = year if year is not None else datetime.now().year
    sessions_payload = _get_json("sessions", params={"year": target_year})
    if not sessions_payload:
        return {
            "drivers": [],
            "teams": [],
            "session_label": None,
        }

    meetings_payload = _get_json("meetings", params={"year": target_year})
    meeting_name_by_key = {
        m["meeting_key"]: m.get("meeting_name")
        for m in meetings_payload
        if isinstance(m, dict) and m.get("meeting_key")
    }

    now = datetime.now(BERLIN_TZ)
    race_sessions = []
    for session in sessions_payload:
        if session.get("session_type") != "Race":
            continue
        if session.get("session_name") != "Race":
            continue

        session_start = _parse_iso_datetime(session.get("date_start"))
        if not session_start or session_start > now:
            continue

        race_sessions.append(session)

    if not race_sessions:
        return {
            "drivers": [],
            "teams": [],
            "session_label": None,
        }

    sorted_race_sessions = sorted(
        race_sessions,
        key=lambda s: s.get("date_start") or "",
        reverse=True,
    )

    # OpenF1 championship endpoints currently provide bulk snapshots and may not
    # support session/year filters reliably. Fetch once and filter locally.
    drivers_all = _get_json("championship_drivers")
    teams_all = _get_json("championship_teams")

    drivers_by_session = {}
    for row in drivers_all:
        if not isinstance(row, dict):
            continue
        session_key = row.get("session_key")
        if not session_key:
            continue
        drivers_by_session.setdefault(session_key, []).append(row)

    teams_by_session = {}
    for row in teams_all:
        if not isinstance(row, dict):
            continue
        session_key = row.get("session_key")
        if not session_key:
            continue
        teams_by_session.setdefault(session_key, []).append(row)

    latest_race = None
    drivers_standings = []
    teams_standings = []
    drivers_payload = []

    # Some race sessions can exist before championship snapshots are published.
    # Walk backward until we find the newest session with standings data.
    for candidate_session in sorted_race_sessions:
        session_key = candidate_session.get("session_key")
        if not session_key:
            continue

        candidate_drivers = drivers_by_session.get(session_key, [])
        candidate_teams = teams_by_session.get(session_key, [])

        if not candidate_drivers and not candidate_teams:
            continue

        latest_race = candidate_session
        drivers_standings = candidate_drivers
        teams_standings = candidate_teams
        drivers_payload = _get_json("drivers", params={"session_key": session_key})
        break

    if latest_race is None:
        return {
            "drivers": [],
            "teams": [],
            "session_label": None,
        }

    driver_name_by_number = {}
    driver_team_by_number = {}
    for driver in drivers_payload:
        driver_number = driver.get("driver_number")
        if not driver_number:
            continue
        driver_name_by_number[driver_number] = _format_driver_display_name(
            driver,
            driver_number=driver_number,
        )
        driver_team_by_number[driver_number] = driver.get("team_name")

    drivers = []
    for row in drivers_standings:
        driver_number = row.get("driver_number")
        current_position = row.get("position_current")
        current_points = row.get("points_current")
        if current_position is None or current_points is None:
            continue
        drivers.append(
            {
                "driver_number": driver_number,
                "position": current_position,
                "name": driver_name_by_number.get(driver_number, f"#{driver_number}"),
                "points": int(current_points),
                "team_logo": _get_team_logo_url(driver_team_by_number.get(driver_number)),
            }
        )

    teams = []
    for row in teams_standings:
        current_position = row.get("position_current")
        current_points = row.get("points_current")
        team_name = row.get("team_name")
        if current_position is None or current_points is None or not team_name:
            continue
        teams.append(
            {
                "position": current_position,
                "name": team_name,
                "points": int(current_points),
                "team_logo": _get_team_logo_url(team_name),
            }
        )

    drivers.sort(key=lambda x: x["position"])
    teams.sort(key=lambda x: x["position"])

    session_label = (
        latest_race.get("meeting_name")
        or meeting_name_by_key.get(latest_race.get("meeting_key"))
    )

    # ── Sprint-Punkte einrechnen ───────────────────────────────────────────────
    # Hat nach dem letzten GP-Rennen ein Sprint stattgefunden, wird dessen
    # kumulatives points_current per driver_number in die Standings übernommen
    # und die Positionen werden neu berechnet.
    # OpenF1 liefert Sprint-Daten nur partiell (nicht alle 20 Fahrer erscheinen),
    # daher werden nur die vorhandenen Einträge aktualisiert.
    latest_race_date_str = latest_race.get("date_start") or ""
    sprint_sessions_later = sorted(
        [
            s for s in sessions_payload
            if s.get("session_name") == "Sprint"
            and s.get("session_type") == "Race"
            and (s.get("date_start") or "") > latest_race_date_str
            and _parse_iso_datetime(s.get("date_start")) is not None
            and _parse_iso_datetime(s.get("date_start")) <= now
        ],
        key=lambda s: s.get("date_start") or "",
        reverse=True,
    )

    for sprint_session in sprint_sessions_later:
        sprint_key = sprint_session.get("session_key")
        if not sprint_key:
            continue

        # Fahrerpunkte aus Sprint-Snapshot
        sprint_driver_rows = drivers_by_session.get(sprint_key, [])
        sprint_points_by_number = {
            row["driver_number"]: int(row["points_current"])
            for row in sprint_driver_rows
            if row.get("driver_number") is not None and row.get("points_current") is not None
        }
        if not sprint_points_by_number:
            continue

        for driver in drivers:
            dn = driver.get("driver_number")
            if dn is not None and dn in sprint_points_by_number:
                driver["points"] = sprint_points_by_number[dn]

        drivers.sort(key=lambda d: d["points"], reverse=True)
        for pos, driver in enumerate(drivers, 1):
            driver["position"] = pos

        # Konstrukteure: Sprint-Teamdaten direkt verwenden wenn vorhanden,
        # sonst aus den aktualisierten Fahrerpunkten neu aggregieren.
        sprint_team_rows = teams_by_session.get(sprint_key, [])
        sprint_team_points = {
            row["team_name"]: int(row["points_current"])
            for row in sprint_team_rows
            if row.get("team_name") and row.get("points_current") is not None
        }
        if sprint_team_points:
            for team in teams:
                if team["name"] in sprint_team_points:
                    team["points"] = sprint_team_points[team["name"]]
        else:
            team_totals: dict = {}
            for driver in drivers:
                dn = driver.get("driver_number")
                team_name = driver_team_by_number.get(dn) if dn is not None else None
                if team_name:
                    team_totals[team_name] = team_totals.get(team_name, 0) + driver["points"]
            for team in teams:
                if team["name"] in team_totals:
                    team["points"] = team_totals[team["name"]]

        teams.sort(key=lambda t: t["points"], reverse=True)
        for pos, team in enumerate(teams, 1):
            team["position"] = pos

        sprint_meeting_label = (
            sprint_session.get("meeting_name")
            or meeting_name_by_key.get(sprint_session.get("meeting_key"))
        )
        if sprint_meeting_label:
            base = sprint_meeting_label.replace(" Grand Prix", "")
            session_label = f"{base} Sprint"

        break  # nur den neuesten Sprint verwenden

    return {
        "drivers": drivers,
        "teams": teams,
        "session_label": session_label,
    }
