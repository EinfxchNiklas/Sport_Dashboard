import requests
from datetime import datetime

def fetch_bvb_matches():
    base_url = "https://api.openligadb.de"
    league_shortcuts = ["bl1", "dfb", "cl"]  # Bundesliga, DFB Pokal, Champions League
    season = 2025  # Current season
    team_id = 7  # Borussia Dortmund's team ID

    matches = []

    for league in league_shortcuts:
        # Fetch all matches for the league and season
        league_matches_url = f"{base_url}/getmatchdata/{league}/{season}"
        response = requests.get(league_matches_url)
        if response.status_code == 200:
            league_matches = response.json()

            # Filter matches involving Borussia Dortmund
            bvb_matches = [
                match for match in league_matches
                if match['team1']['teamId'] == team_id or match['team2']['teamId'] == team_id
            ]

            # Sort matches by date
            bvb_matches.sort(key=lambda x: x['matchDateTime'])

            # Separate past and future matches
            now = datetime.now()
            past_matches = [match for match in bvb_matches if datetime.fromisoformat(match['matchDateTime']) < now]
            future_matches = [match for match in bvb_matches if datetime.fromisoformat(match['matchDateTime']) >= now]

            # Format dates for display
            for match in bvb_matches:
                match['formattedDateTime'] = datetime.fromisoformat(match['matchDateTime']).strftime('%H:%M %d.%m.%Y')

            # Add last 4 past matches and next 5 future matches
            matches.extend(past_matches[-4:])  # Last 4 matches
            matches.extend(future_matches[:5])  # Next 5 matches

    return matches

if __name__ == "__main__":
    bvb_matches = fetch_bvb_matches()
    for match in bvb_matches:
        print(match)