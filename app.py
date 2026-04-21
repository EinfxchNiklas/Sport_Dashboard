from flask import Flask, Response, jsonify, render_template, request
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from data_sources.get_fussball_data import (
    fetch_team_matches,
    fetch_bundesliga_table,
)
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

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7  # 1 Woche


def _find_latest_available_nfl_week(season, season_type, max_week):
    """Return latest week/round that has at least one game for the given season/type."""
    for week in range(max_week, 0, -1):
        games, rate_limited = fetch_nfl_scores(season, week, season_type)
        if rate_limited:
            break
        if games:
            return week, games, False
    return 1, None, False

@app.route('/')
def homepage():
    return render_template('homepage.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/favicon.ico')
def favicon():
    # Avoid repeated 404s if no favicon file is configured yet.
    return Response(status=204)


@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_probe():
    # Chrome DevTools may probe this path; returning 204 keeps logs clean.
    return Response(status=204)

@app.route('/fussball')
def display_matches():
    team_id = request.args.get('team', 4, type=int)
    
    standings, standings_rate_limited = fetch_bundesliga_table()
    matches, matches_rate_limited = fetch_team_matches(team_id)
    
    api_rate_limited = standings_rate_limited or matches_rate_limited
    
    selected_team = next((t for t in standings if t.get('teamId') == team_id), None)
    selected_team_name = selected_team['teamName'] if selected_team else 'Bundesliga'
    
    return render_template(
        'fussball.html',
        matches=matches,
        standings=standings,
        selected_team_id=team_id,
        selected_team_name=selected_team_name,
        api_rate_limited=api_rate_limited,
        api_block_seconds_left=60 if api_rate_limited else 0,
    )

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
    now = datetime.now()
    current_season = now.year if now.month >= 8 else now.year - 1
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
    current_season = now.year if now.month >= 8 else now.year - 1
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


@app.route('/impressum')
def impressum():
    return render_template('impressum.html')


if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('DEBUG')
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=True)
