import hashlib
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import hmac
import requests
from dotenv import load_dotenv

from data_sources.get_formula1_data import fetch_formula1_weekends
from data_sources.get_nfl_data import fetch_nfl_scores

load_dotenv()

BERLIN_TZ = ZoneInfo('Europe/Berlin')
_OPENLIGADB_BASE = (os.environ.get('OPENLIGADB_BASE_URL') or '').rstrip('/')

_EXPORT_FOOTBALL_COMPETITIONS = (
    ('bl1', 'Bundesliga'),
    ('dfb', 'DFB-Pokal'),
    ('ucl', 'Champions League'),
)

_F1_SESSION_DURATIONS = {
    'Race': timedelta(hours=2),
    'Sprint': timedelta(minutes=45),
    'Qualifying': timedelta(hours=1, minutes=15),
    'Sprint Qualifying': timedelta(hours=1, minutes=15),
    'Sprint Shootout': timedelta(hours=1, minutes=15),
    'Practice 1': timedelta(hours=1),
    'Practice 2': timedelta(hours=1),
    'Practice 3': timedelta(hours=1),
}

_NFL_TEAM_NAMES = {
    'ARI': 'Cardinals',
    'ATL': 'Falcons',
    'BAL': 'Ravens',
    'BUF': 'Bills',
    'CAR': 'Panthers',
    'CHI': 'Bears',
    'CIN': 'Bengals',
    'CLE': 'Browns',
    'DAL': 'Cowboys',
    'DEN': 'Broncos',
    'DET': 'Lions',
    'GB': 'Packers',
    'HOU': 'Texans',
    'IND': 'Colts',
    'JAX': 'Jaguars',
    'KC': 'Chiefs',
    'LAR': 'Rams',
    'LAC': 'Chargers',
    'LV': 'Raiders',
    'MIA': 'Dolphins',
    'MIN': 'Vikings',
    'NE': 'Patriots',
    'NO': 'Saints',
    'NYG': 'Giants',
    'NYJ': 'Jets',
    'PHI': 'Eagles',
    'PIT': 'Steelers',
    'SEA': 'Seahawks',
    'SF': '49ers',
    'TB': 'Buccaneers',
    'TEN': 'Titans',
    'WAS': 'Commanders',
    'WSH': 'Commanders',
}


def has_valid_basic_auth(auth, expected_username, expected_password):
    if not auth:
        return False

    if not expected_username or not expected_password:
        return False

    return (
        hmac.compare_digest(str(auth.username or ''), str(expected_username))
        and hmac.compare_digest(str(auth.password or ''), str(expected_password))
    )


def _parse_iso_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def _parse_berlin_datetime(date_value, time_value):
    if not date_value or not time_value:
        return None

    try:
        parsed = datetime.strptime(f"{date_value} {time_value}", '%d.%m.%Y %H:%M')
        return parsed.replace(tzinfo=BERLIN_TZ)
    except ValueError:
        return None


def _escape_ics_text(value):
    text = str(value or '')
    return (
        text.replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _to_ics_utc(dt_value):
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def build_ics(events):
    now_utc = datetime.now(timezone.utc)
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Sport Dashboard//Calendar Export//DE',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]

    for event in sorted(events, key=lambda item: item['start']):
        uid_seed = (
            f"{event.get('summary', '')}|"
            f"{event['start'].isoformat()}|"
            f"{event['end'].isoformat()}|"
            f"{event.get('all_day', False)}"
        )
        uid = f"{hashlib.md5(uid_seed.encode('utf-8')).hexdigest()}@sport-dashboard"

        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:{uid}')
        lines.append(f'DTSTAMP:{_to_ics_utc(now_utc)}')

        if event.get('all_day'):
            start_local = event['start'].astimezone(BERLIN_TZ)
            end_local = event['end'].astimezone(BERLIN_TZ)
            lines.append(f"DTSTART;VALUE=DATE:{start_local.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{end_local.strftime('%Y%m%d')}")
        else:
            lines.append(f"DTSTART:{_to_ics_utc(event['start'])}")
            lines.append(f"DTEND:{_to_ics_utc(event['end'])}")

        lines.append(f"SUMMARY:{_escape_ics_text(event.get('summary'))}")

        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines) + '\r\n'


def _duration_for_f1_session(session_name):
    return _F1_SESSION_DURATIONS.get(session_name, timedelta(hours=1))


def _nfl_team_display_name(team_abbreviation):
    abbreviation = str(team_abbreviation or '').upper()
    return _NFL_TEAM_NAMES.get(abbreviation, abbreviation or 'Team')


def _format_f1_session_title(session_name):
    if session_name == 'Practice 1':
        normalized = 'FP1'
    elif session_name == 'Practice 2':
        normalized = 'FP2'
    elif session_name == 'Practice 3':
        normalized = 'FP3'
    elif session_name in {'Sprint Qualifying', 'Sprint Shootout'}:
        normalized = 'Sprint Qualifying'
    elif session_name == 'Sprint':
        normalized = 'Sprint Rennen'
    elif session_name == 'Race':
        normalized = 'Rennen'
    elif session_name == 'Qualifying':
        normalized = 'Qualifying'
    else:
        normalized = session_name or 'Session'

    return f'{normalized}'


def _dedupe_events(events):
    unique = {}
    for event in events:
        key = (
            event.get('summary', ''),
            event['start'].isoformat(),
            event['end'].isoformat(),
            bool(event.get('all_day', False)),
        )
        if key not in unique:
            unique[key] = event
    return list(unique.values())


def _current_football_season_for_export():
    now = datetime.now(BERLIN_TZ)
    return now.year if now.month >= 7 else now.year - 1


def _current_nfl_season_for_export():
    now = datetime.now(BERLIN_TZ)
    return now.year if now.month >= 5 else now.year - 1


def _parse_openligadb_match_start(raw_match):
    start_utc = _parse_iso_datetime(raw_match.get('matchDateTimeUTC'))
    if start_utc is not None:
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        return start_utc.astimezone(timezone.utc)

    start_local = _parse_iso_datetime(raw_match.get('matchDateTime'))
    if start_local is not None:
        if start_local.tzinfo is None:
            start_local = start_local.replace(tzinfo=BERLIN_TZ)
        return start_local.astimezone(timezone.utc)

    return None


def _fetch_openligadb_matches(shortcut, season):
    if not _OPENLIGADB_BASE:
        return []

    try:
        response = requests.get(
            f"{_OPENLIGADB_BASE}/getmatchdata/{shortcut}/{season}",
            timeout=20,
        )
        if response.status_code != 200:
            return []

        payload = response.json()
        return payload if isinstance(payload, list) else []
    except requests.RequestException:
        return []


def _collect_football_season_events_for_team(team_label, team_aliases, season=None):
    target_season = season if season is not None else _current_football_season_for_export()
    aliases = tuple(a.lower() for a in team_aliases)
    events = []

    for shortcut, competition_name in _EXPORT_FOOTBALL_COMPETITIONS:
        raw_matches = _fetch_openligadb_matches(shortcut, target_season)
        for raw_match in raw_matches:
            team1_name = str(raw_match.get('team1', {}).get('teamName', ''))
            team2_name = str(raw_match.get('team2', {}).get('teamName', ''))
            team1_name_lower = team1_name.lower()
            team2_name_lower = team2_name.lower()

            if not any(
                alias in team1_name_lower or alias in team2_name_lower
                for alias in aliases
            ):
                continue

            start = _parse_openligadb_match_start(raw_match)
            if start is None:
                continue

            events.append(
                {
                    'start': start,
                    'end': start + timedelta(hours=2),
                    'summary': f"{team1_name or 'Team 1'} vs. {team2_name or 'Team 2'}",
                    'all_day': False,
                }
            )

    return events


def _collect_f1_events(include_sessions, include_weekend_label, season_year=None):
    target_year = season_year if season_year is not None else datetime.now(BERLIN_TZ).year
    weekends = fetch_formula1_weekends(limit=None, year=target_year, timeframe='all')
    events = []

    for weekend in weekends:
        weekend_name = weekend.get('meeting_name', 'Grand Prix')
        weekend_location = weekend.get('location', '')
        weekend_country = weekend.get('country_name', '')
        sessions = weekend.get('sessions', [])
        session_starts = []

        for session_entry in sessions:
            session_name = session_entry.get('session_name', 'Session')
            session_start = _parse_iso_datetime(session_entry.get('date_start'))
            if session_start is None:
                continue

            session_starts.append(session_start)

            if include_sessions:
                duration = _duration_for_f1_session(session_name)
                events.append(
                    {
                        'start': session_start,
                        'end': session_start + duration,
                        'summary': _format_f1_session_title(session_name),
                        'all_day': False,
                    }
                )

        if include_weekend_label and session_starts:
            first_local = min(session_starts).astimezone(BERLIN_TZ)
            last_local = max(session_starts).astimezone(BERLIN_TZ)

            all_day_start = datetime(
                year=first_local.year,
                month=first_local.month,
                day=first_local.day,
                tzinfo=BERLIN_TZ,
            )
            all_day_end = datetime(
                year=last_local.year,
                month=last_local.month,
                day=last_local.day,
                tzinfo=BERLIN_TZ,
            ) + timedelta(days=1)

            events.append(
                {
                    'start': all_day_start,
                    'end': all_day_end,
                    'summary': f"{weekend_name} Rennwochenende",
                    'all_day': True,
                }
            )

    return events


def _collect_nfl_events_for_team(team_abbreviation, season=None):
    target_season = season if season is not None else _current_nfl_season_for_export()

    season_type_specs = (
        ('reg', 18, 'Regular Season'),
        ('post', 4, 'Playoffs'),
    )
    events = []

    for season_type, max_week, season_label in season_type_specs:
        for week in range(1, max_week + 1):
            matches, _ = fetch_nfl_scores(target_season, week, season_type)

            for match in matches:
                home_team = str(match.get('homeTeam', '')).upper()
                away_team = str(match.get('awayTeam', '')).upper()
                if team_abbreviation not in {home_team, away_team}:
                    continue

                home_team_name = _nfl_team_display_name(home_team)
                away_team_name = _nfl_team_display_name(away_team)

                start = _parse_berlin_datetime(
                    match.get('kickoff_date_de'),
                    match.get('kickoff_time_de'),
                )
                if start is None:
                    continue

                events.append(
                    {
                        'start': start,
                        'end': start + timedelta(hours=4),
                        'summary': f"{away_team_name} @ {home_team_name}",
                        'all_day': False,
                    }
                )

    return events


def collect_calendar_export_events(options):
    football_season = _current_football_season_for_export()
    f1_season_year = datetime.now(BERLIN_TZ).year
    nfl_season = _current_nfl_season_for_export()
    events = []

    if options.get('football_dortmund'):
        events.extend(
            _collect_football_season_events_for_team(
                'Borussia Dortmund',
                ('borussia dortmund', 'dortmund'),
                season=football_season,
            )
        )

    if options.get('football_bremen'):
        events.extend(
            _collect_football_season_events_for_team(
                'Werder Bremen',
                ('sv werder bremen', 'werder bremen', 'werder', 'bremen'),
                season=football_season,
            )
        )

    if options.get('f1_sessions') or options.get('f1_weekend_all_day'):
        events.extend(
            _collect_f1_events(
                include_sessions=bool(options.get('f1_sessions')),
                include_weekend_label=bool(options.get('f1_weekend_all_day')),
                season_year=f1_season_year,
            )
        )

    if options.get('nfl_chiefs'):
        events.extend(_collect_nfl_events_for_team('KC', season=nfl_season))

    if options.get('nfl_bengals'):
        events.extend(_collect_nfl_events_for_team('CIN', season=nfl_season))

    return _dedupe_events(events)
