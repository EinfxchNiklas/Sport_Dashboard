from flask import Flask, render_template, request
from data_sources.get_fussball_data import fetch_team_matches, fetch_bundesliga_table

app = Flask(__name__)

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/fussball')
def display_matches():
    team_id = request.args.get('team', 4, type=int)
    standings = fetch_bundesliga_table()
    matches = fetch_team_matches(team_id)
    selected_team = next((t for t in standings if t.get('teamId') == team_id), None)
    selected_team_name = selected_team['teamName'] if selected_team else 'Bundesliga'
    return render_template(
        'matches.html',
        matches=matches,
        standings=standings,
        selected_team_id=team_id,
        selected_team_name=selected_team_name,
    )

@app.route('/formula1')
def formula1_placeholder():
    return render_template('placeholder.html', sport="Formula 1")

@app.route('/american_football')
def american_football_placeholder():
    return render_template('placeholder.html', sport="American Football")

if __name__ == '__main__':
    app.run(debug=True)
