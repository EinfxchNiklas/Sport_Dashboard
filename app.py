from flask import Flask, jsonify, render_template, request
from concurrent.futures import ThreadPoolExecutor
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
)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7  # 1 Woche

@app.route('/')
def homepage():
    return render_template('homepage.html')

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
    season_type = request.args.get('type', 'reg', type=str)
    if season_type not in ('reg', 'post'):
        season_type = 'reg'

    if season_type == 'reg':
        selected_week = request.args.get('week', 1, type=int)
        if selected_week < 1:
            selected_week = 1
        if selected_week > 18:
            selected_week = 18
        available_weeks = [(w, f'Woche {w}') for w in range(1, 19)]
    else:
        selected_week = request.args.get('week', 1, type=int)
        if selected_week < 1:
            selected_week = 1
        if selected_week > 4:
            selected_week = 4
        available_weeks = [
            (1, 'Wild Card'),
            (2, 'Divisional Round'),
            (3, 'Conference Championship'),
            (4, 'Super Bowl'),
        ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        scores_future = executor.submit(fetch_nfl_scores, None, selected_week, season_type)
        teams_future = executor.submit(fetch_nfl_teams)

        scores, scores_rate_limited = scores_future.result()
        teams, teams_rate_limited = teams_future.result()

    standings = build_nfl_standings_from_teams(teams)
    standings_rate_limited = False if standings else teams_rate_limited

    api_rate_limited = scores_rate_limited or standings_rate_limited or teams_rate_limited

    all_teams = [
        {
            'id': t.get('teamAbv', ''),
            'name': f"{t.get('teamCity', '').strip()} {t.get('teamName', '').strip()}".strip(),
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
        season_type=season_type,
        all_teams=all_teams,
        league_standings=league_standings,
        standings_data=standings,
        api_rate_limited=api_rate_limited,
        api_block_seconds_left=60 if api_rate_limited else 0,
    )


@app.route('/american_football/week-results')
def american_football_week_results():
    season_type = request.args.get('type', 'reg', type=str)
    if season_type not in ('reg', 'post'):
        season_type = 'reg'

    selected_week = request.args.get('week', 1, type=int)
    max_week = 18 if season_type == 'reg' else 4
    if selected_week < 1:
        selected_week = 1
    if selected_week > max_week:
        selected_week = max_week

    scores, scores_rate_limited = fetch_nfl_scores(week=selected_week, season_type=season_type)
    enriched_matches, boxscores_rate_limited = enrich_matches_with_boxscores(scores)

    return jsonify(
        {
            'week': selected_week,
            'matches': enriched_matches,
            'api_rate_limited': scores_rate_limited or boxscores_rate_limited,
        }
    )

if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('DEBUG')
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=True)
