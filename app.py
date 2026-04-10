from flask import Flask, jsonify, render_template, request
from data_sources.get_fussball_data import (
    fetch_team_matches,
    fetch_bundesliga_table,
)
from data_sources.get_formula1_data import (
    fetch_formula1_weekends,
    fetch_championship_standings,
    fetch_meeting_session_result_summaries,
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
def american_football_placeholder():
    return render_template('placeholder.html', sport="American Football")

if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('DEBUG', 'False') == 'True'
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=True)
