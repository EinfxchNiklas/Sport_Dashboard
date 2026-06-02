from flask import Flask, Response, jsonify, render_template, request
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from data_sources.calendar_export import (
    BERLIN_TZ,
    build_ics,
    collect_calendar_export_events,
    has_valid_basic_auth,
)
from data_sources.get_fussball_data import (
    fetch_team_matches,
    fetch_bundesliga_table,
    fetch_cl_data,
    fetch_cl_ligaphase_table,
    fetch_dfb_data,
    fetch_wm_data,
)
from data_sources.get_injured_players import fetch_injured_players
from data_sources.get_formula1_data import (
    fetch_formula1_weekends,
    fetch_championship_standings,
    fetch_meeting_session_result_summaries,
)
from data_sources.get_nfl_data import (
    fetch_nfl_scores,
    fetch_nfl_teams,
    build_nfl_standings_from_teams,
    enrich_matches_with_boxscores,
    organize_matches_by_team,
    get_complete_league_standings,
    get_conference_standings,
    get_division_standings,
    fetch_nfl_team_roster,
    get_team_logo_path,
    POSITION_ORDER,
)

load_dotenv()

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7  # 1 Woche
app.config['UMAMI_SCRIPT_URL'] = (os.environ.get('UMAMI_SCRIPT_URL') or '').strip()
app.config['UMAMI_WEBSITE_ID'] = (os.environ.get('UMAMI_WEBSITE_ID') or '').strip()
app.config['EXPORT_USERNAME'] = (os.environ.get('EXPORT_USERNAME') or '').strip()
app.config['EXPORT_PASSWORD'] = os.environ.get('EXPORT_PASSWORD') or ''


def _basic_auth_challenge_response():
    response = Response('Authentication required', status=401)
    response.headers['WWW-Authenticate'] = 'Basic realm="Sport Dashboard Export"'
    return response


def _require_export_auth(route_handler):
    @wraps(route_handler)
    def _wrapped(*args, **kwargs):
        if has_valid_basic_auth(
            request.authorization,
            app.config.get('EXPORT_USERNAME', ''),
            app.config.get('EXPORT_PASSWORD', ''),
        ):
            return route_handler(*args, **kwargs)

        return _basic_auth_challenge_response()

    return _wrapped


class _HumanTrafficLogFilter(logging.Filter):
    EXCLUDED_PATH_SNIPPETS = (
        ' /health ',
        '/.well-known/appspecific/com.chrome.devtools.json',
    )

    EXCLUDED_BOT_SNIPPETS = (
        'uptimerobot',
        'kube-probe',
        'pingdom',
        'statuscake',
        'healthcheck',
    )

    def filter(self, record):
        message = record.getMessage().lower()

        if any(path in message for path in self.EXCLUDED_PATH_SNIPPETS):
            return False

        if any(bot in message for bot in self.EXCLUDED_BOT_SNIPPETS):
            return False

        return True


def _configure_runtime_log_filters():
    log_filter = _HumanTrafficLogFilter()
    for logger_name in ('werkzeug', 'gunicorn.access'):
        logger = logging.getLogger(logger_name)
        logger.addFilter(log_filter)


_configure_runtime_log_filters()


@app.context_processor
def inject_analytics_config():
    script_url = app.config.get('UMAMI_SCRIPT_URL', '')
    website_id = app.config.get('UMAMI_WEBSITE_ID', '')
    enabled = bool(script_url and website_id)
    return {
        'umami_enabled': enabled,
        'umami_script_url': script_url,
        'umami_website_id': website_id,
    }


def _check_website_health():
    """Validate basic app routing footprint to represent website readiness."""
    required_routes = {
        '/',
        '/fussball',
        '/fussball/bundesliga',
        '/formula1',
        '/american_football',
    }
    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}
    missing_routes = sorted(required_routes - registered_routes)

    return {
        'status': 'ok' if not missing_routes else 'error',
        'route_count': len(registered_routes),
        'missing_routes': missing_routes,
    }



def _is_nfl_game_pending(game):
    """Return True if a game is not fully completed yet."""
    status_code = str(game.get('statusCode', '')).strip()
    status = str(game.get('status', '')).strip().lower()

    # API uses status code 0 for scheduled/not started games.
    if status_code == '0':
        return True

    # Keep live or interrupted games in the currently selected week.
    pending_markers = (
        'live',
        'in progress',
        'quarter',
        'q1',
        'q2',
        'q3',
        'q4',
        'ot',
        'halftime',
        'delayed',
        'postponed',
        'suspended',
    )
    return any(marker in status for marker in pending_markers)


def _find_latest_available_nfl_week(season, season_type, max_week):
    """Return the first not-yet-completed week for the given season/type."""
    fallback_week = 1

    for week in range(1, max_week + 1):
        games, rate_limited = fetch_nfl_scores(season, week, season_type)
        if rate_limited:
            return fallback_week, None, True

        if not games:
            return week, None, False

        if any(_is_nfl_game_pending(game) for game in games):
            return week, games, False

        fallback_week = min(week + 1, max_week)

    return fallback_week, None, False

@app.route('/')
def homepage():
    return render_template('homepage.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')


@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_probe():
    # Chrome DevTools may probe this path; returning 204 keeps logs clean.
    return Response(status=204)


@app.route('/health', methods=['GET'])
def healthcheck():
    checked_at = datetime.utcnow().isoformat() + 'Z'
    website = _check_website_health()

    if website['status'] == 'error':
        overall_status = 'down'
        http_code = 503
    else:
        overall_status = 'ok'
        http_code = 200

    if request.method == 'HEAD':
        return Response(status=http_code)

    return jsonify(
        {
            'status': overall_status,
            'checked_at': checked_at,
            'website': website,
        }
    ), http_code

@app.route('/fussball')
def fussball_selector():
    from data_sources._openligadb_common import _current_football_season
    year = _current_football_season()
    season_label = f"{year}/{(year + 1) % 100:02d}"
    return render_template('fussball_select.html', season_label=season_label)


@app.route('/fussball/bundesliga')
def display_matches():
    team_id = request.args.get('team', 7, type=int)
    source = request.args.get('source', 'home', type=str)
    if source not in {'home', 'select'}:
        source = 'home'

    standings, _ = fetch_bundesliga_table()
    matches, _ = fetch_team_matches(team_id)

    selected_team = next((t for t in standings if t.get('teamId') == team_id), None)
    selected_team_name = selected_team['teamName'] if selected_team else 'Bundesliga'

    return render_template(
        'fussball.html',
        matches=matches,
        standings=standings,
        selected_team_id=team_id,
        selected_team_name=selected_team_name,
        source=source,
        home_url='/fussball' if source == 'select' else '/',
        home_label='Wettbewerbe' if source == 'select' else 'Home',
    )


@app.route('/fussball/bundesliga/verletzte')
def bundesliga_injured_players():
    team_id = request.args.get('team', 7, type=int)

    standings, _ = fetch_bundesliga_table()
    selected_team = next((t for t in standings if t.get('teamId') == team_id), None)
    team_name = selected_team['teamName'] if selected_team else None

    if team_name is None:
        return jsonify({'players': [], 'error': 'unknown_team'}), 404

    players, error = fetch_injured_players(team_name)
    return jsonify({'players': players, 'error': error, 'teamName': team_name})


@app.route('/fussball/champions-league')
def fussball_cl():
    phase_order_id = request.args.get('phase', type=int)
    spieltag_idx = request.args.get('spieltag', None, type=int)

    data = fetch_cl_data(
        phase_order_id=phase_order_id,
        spieltag_idx=spieltag_idx,
        include_table=False,
    )
    return render_template('fussball_cl.html', **data)


@app.route('/api/fussball/champions-league/table')
def fussball_cl_table_api():
    table = fetch_cl_ligaphase_table()
    return jsonify({'table': table})


@app.route('/fussball/dfb-pokal')
def fussball_dfb():
    round_order_id = request.args.get('runde', type=int)
    data = fetch_dfb_data(round_order_id=round_order_id)
    return render_template('fussball_dfb.html', **data)


@app.route('/fussball/wm')
def fussball_wm():
    phase_order_id = request.args.get('phase', 1, type=int)
    data = fetch_wm_data(phase_order_id=phase_order_id)
    return render_template('fussball_wm.html', **data)


@app.route('/formula1')
def formula1_dashboard():
    upcoming_weekends = fetch_formula1_weekends(limit=None, timeframe='upcoming')
    championship = fetch_championship_standings()
    return render_template(
        'formula1.html',
        upcoming_weekends=upcoming_weekends,
        past_weekends=[],
        championship=championship,
    )


@app.route('/formula1/past-weekends')
def formula1_past_weekends():
    past_weekends = fetch_formula1_weekends(
        limit=None,
        timeframe='past',
        include_session_results=False,
    )
    return jsonify(past_weekends)


@app.route('/formula1/past-weekends/<int:meeting_key>/results')
def formula1_past_weekend_results(meeting_key):
    return jsonify(fetch_meeting_session_result_summaries(meeting_key))

@app.route('/american_football')
def american_football():
    # Keep season choices aligned with available API data.
    # From May onward the new season year is used as default (playoffs/Super Bowl
    # run through April, so January through April still belong to the previous season).
    now = datetime.now()
    current_season = now.year if now.month >= 5 else now.year - 1
    min_available_season = 2022
    max_available_season = max(now.year, current_season)

    available_seasons = [(y, str(y)) for y in range(min_available_season, max_available_season + 1)]

    selected_season = request.args.get('season', current_season, type=int)
    if selected_season < min_available_season or selected_season > max_available_season:
        selected_season = current_season
    
    season_type = request.args.get('type', 'reg', type=str)
    if season_type not in ('reg', 'post'):
        season_type = 'reg'

    if season_type == 'reg':
        max_week = 18
        available_weeks = [(w, f'Woche {w}') for w in range(1, 19)]
    else:
        max_week = 4
        available_weeks = [
            (1, 'Wild Card'),
            (2, 'Divisional Round'),
            (3, 'Conference Championship'),
            (4, 'Super Bowl'),
        ]

    week_param = request.args.get('week', type=int)
    prefetched_scores = None
    prefetched_scores_rate_limited = False

    if week_param is None:
        selected_week, prefetched_scores, prefetched_scores_rate_limited = _find_latest_available_nfl_week(
            selected_season,
            season_type,
            max_week,
        )
    else:
        selected_week = week_param
        if selected_week < 1:
            selected_week = 1
        if selected_week > max_week:
            selected_week = max_week

    if prefetched_scores is None:
        with ThreadPoolExecutor(max_workers=2) as executor:
            scores_future = executor.submit(fetch_nfl_scores, selected_season, selected_week, season_type)
            teams_future = executor.submit(fetch_nfl_teams)

            scores, scores_rate_limited = scores_future.result()
            teams, teams_rate_limited = teams_future.result()
    else:
        scores = prefetched_scores
        scores_rate_limited = prefetched_scores_rate_limited
        teams, teams_rate_limited = fetch_nfl_teams()

    standings = build_nfl_standings_from_teams(teams)
    standings_rate_limited = False if standings else teams_rate_limited

    api_rate_limited = scores_rate_limited or standings_rate_limited or teams_rate_limited

    all_teams = [
        {
            'id': t.get('teamAbv', ''),
            'name': f"{t.get('teamCity', '').strip()} {t.get('teamName', '').strip()}".strip(),
            'logo': get_team_logo_path(t.get('teamAbv', '')),
        }
        for t in teams
        if t.get('teamAbv')
    ]
    all_teams.sort(key=lambda t: t['name'])

    week_matches = scores

    league_standings = get_complete_league_standings(standings)
    selected_week_label = next((lbl for w, lbl in available_weeks if w == selected_week), str(selected_week))

    return render_template(
        'american_football.html',
        week_matches=week_matches,
        selected_week=selected_week,
        selected_week_label=selected_week_label,
        available_weeks=available_weeks,
        available_seasons=available_seasons,
        selected_season=selected_season,
        current_season=current_season,
        season_type=season_type,
        all_teams=all_teams,
        league_standings=league_standings,
        standings_data=standings,
        api_rate_limited=api_rate_limited,
        api_block_seconds_left=60 if api_rate_limited else 0,
    )


@app.route('/american_football/week-results')
def american_football_week_results():
    # Keep season query consistent with the season selector bounds.
    now = datetime.now()
    current_season = now.year if now.month >= 5 else now.year - 1
    min_available_season = 2022
    max_available_season = max(now.year, current_season)

    selected_season = request.args.get('season', current_season, type=int)
    if selected_season < min_available_season or selected_season > max_available_season:
        selected_season = current_season
    season_type = request.args.get('type', 'reg', type=str)
    if season_type not in ('reg', 'post'):
        season_type = 'reg'

    selected_week = request.args.get('week', 1, type=int)
    max_week = 18 if season_type == 'reg' else 4
    if selected_week < 1:
        selected_week = 1
    if selected_week > max_week:
        selected_week = max_week

    scores, scores_rate_limited = fetch_nfl_scores(selected_season, selected_week, season_type)
    enriched_matches, boxscores_rate_limited = enrich_matches_with_boxscores(scores)

    return jsonify(
        {
            'week': selected_week,
            'matches': enriched_matches,
            'api_rate_limited': scores_rate_limited or boxscores_rate_limited,
        }
    )

@app.route('/american_football/roster/<team_abv>')
def american_football_roster(team_abv):
    if not re.match(r'^[A-Z0-9]{1,5}$', team_abv.upper()):
        return jsonify({"error": "Invalid team abbreviation"}), 400

    team_abv = team_abv.upper()
    roster, rate_limited = fetch_nfl_team_roster(team_abv)

    # Group by unit → position
    grouped = {}
    for player in roster:
        unit = player["unit"]
        pos = player["pos"]
        grouped.setdefault(unit, {}).setdefault(pos, []).append(player)

    # Sort players within each position by jersey number
    for unit_data in grouped.values():
        for pos_players in unit_data.values():
            pos_players.sort(key=lambda p: int(p["jerseyNum"]) if str(p["jerseyNum"]).isdigit() else 99)

    return jsonify({
        "teamAbv": team_abv,
        "grouped": grouped,
        "positionOrder": POSITION_ORDER,
        "rate_limited": rate_limited,
    })


@app.route('/calendar-export')
@_require_export_auth
def calendar_export_page():
    return render_template('calendar_export.html')


@app.route('/calendar-export/download', methods=['POST'])
@_require_export_auth
def calendar_export_download():
    options = {
        'football_dortmund': bool(request.form.get('football_dortmund')),
        'football_bremen': bool(request.form.get('football_bremen')),
        'f1_sessions': bool(request.form.get('f1_sessions')),
        'f1_weekend_all_day': bool(request.form.get('f1_weekend_all_day')),
        'nfl_chiefs': bool(request.form.get('nfl_chiefs')),
        'nfl_bengals': bool(request.form.get('nfl_bengals')),
    }

    events = collect_calendar_export_events(options)
    ics_content = build_ics(events)

    filename = f"sport_dashboard_export_{datetime.now(BERLIN_TZ).strftime('%Y%m%d')}.ics"
    response = Response(ics_content, content_type='text/calendar; charset=utf-8')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@app.route('/impressum')
def impressum():
    return render_template('impressum.html')


if __name__ == '__main__':
    debug_mode = os.environ.get('DEBUG')
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=True)
