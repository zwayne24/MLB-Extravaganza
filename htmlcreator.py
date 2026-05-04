import os
import requests
import pandas as pd
import base64
from pathlib import Path
from datetime import date, timedelta, datetime

# Function to convert image to base64
def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def img_to_html(img_path):
    img_html = "<img src='data:image/png;base64,{0}' height='100px' class='img-fluid'>".format(
      img_to_bytes(img_path)
    )
    return img_html

def generate_daily_projection_table(matchups_df, ChasesTeams, BrycesTeams, ZachsTeams, teamToAbbr):
    owner_colors = {
        "Chase": '#2774AE',
        "Bryce": '#57068c',
        "Zach": '#e21833'
    }

    # Create abbreviation → owner map
    owner_map = {}
    for team in ChasesTeams:
        owner_map[teamToAbbr[team]] = "Chase"
    for team in BrycesTeams:
        owner_map[teamToAbbr[team]] = "Bryce"
    for team in ZachsTeams:
        owner_map[teamToAbbr[team]] = "Zach"

    owners = ["Chase", "Bryce", "Zach"]
    results = {owner: {"teams_playing": 0, "max_wins": 0, "min_wins": 0, "favored": 0} for owner in owners}

    for _, row in matchups_df.iterrows():
        home = row["home_team"].strip().upper()
        away = row["away_team"].strip().upper()
        odds = str(row["odds"]).strip().upper()

        owner_home = owner_map.get(home)
        owner_away = owner_map.get(away)

        if not owner_home and not owner_away:
            continue

        if owner_home:
            results[owner_home]["teams_playing"] += 1
        if owner_away:
            results[owner_away]["teams_playing"] += 1

        if owner_home and owner_away:
            if owner_home == owner_away:
                results[owner_home]["max_wins"] += 1
                results[owner_home]["min_wins"] += 1
            else:
                results[owner_home]["max_wins"] += 1
                results[owner_away]["max_wins"] += 1
        else:
            owned = owner_home or owner_away
            results[owned]["max_wins"] += 1

        if "-" in odds:
            favored_team = odds.split(" ")[0].strip()
            favored_owner = owner_map.get(favored_team)
            if favored_owner:
                results[favored_owner]["favored"] += 1

    html = """
    <h3 class="daily-overview-title">Daily Overview</h3>
    <table class="standings-table">
      <tr><th></th><th>Teams Playing</th><th>Max Wins</th><th>Min Wins</th><th>Favored</th></tr>
    """
    for owner in owners:
        color = owner_colors[owner]
        r = results[owner]
        html += f"<tr><td style='color:{color}; font-weight:bold;'>{owner}</td><td>{r['teams_playing']}</td><td>{r['max_wins']}</td><td>{r['min_wins']}</td><td>{r['favored']}</td></tr>"
    html += "</table>"
    return html

# Maps the short team names the MLB Stats API returns to full names used everywhere else
MLB_API_NAME_TO_FULL = {
    'Yankees': 'New York Yankees', 'Mets': 'New York Mets', 'Cubs': 'Chicago Cubs',
    'Braves': 'Atlanta Braves', 'Astros': 'Houston Astros', 'Brewers': 'Milwaukee Brewers',
    'Rangers': 'Texas Rangers', 'Rays': 'Tampa Bay Rays', 'Athletics': 'Athletics',
    'Nationals': 'Washington Nationals', 'Dodgers': 'Los Angeles Dodgers',
    'Phillies': 'Philadelphia Phillies', 'Tigers': 'Detroit Tigers',
    'Giants': 'San Francisco Giants', 'Guardians': 'Cleveland Guardians',
    'Reds': 'Cincinnati Reds', 'Pirates': 'Pittsburgh Pirates',
    'Angels': 'Los Angeles Angels', 'White Sox': 'Chicago White Sox',
    'Rockies': 'Colorado Rockies', 'Blue Jays': 'Toronto Blue Jays',
    'Mariners': 'Seattle Mariners', 'Red Sox': 'Boston Red Sox',
    'Orioles': 'Baltimore Orioles', 'Padres': 'San Diego Padres',
    'Royals': 'Kansas City Royals', 'D-backs': 'Arizona Diamondbacks',
    'Marlins': 'Miami Marlins', 'Twins': 'Minnesota Twins', 'Cardinals': 'St. Louis Cardinals',
}

# Fetch standings from the official MLB Stats API
SEASON = date.today().year
standings_resp = requests.get(
    f'https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={SEASON}&standingsTypes=regularSeason'
)
standings_data = standings_resp.json()

standings = pd.DataFrame(columns=['Team', 'W', 'L', 'PCT'])
for division in standings_data['records']:
    for team_record in division['teamRecords']:
        api_name = team_record['team']['name']
        full_name = MLB_API_NAME_TO_FULL.get(api_name, api_name)
        new_row = pd.DataFrame([{
            'Team': full_name,
            'W': team_record['wins'],
            'L': team_record['losses'],
            'PCT': float(team_record['winningPercentage']),
        }])
        standings = pd.concat([standings, new_row], ignore_index=True)

# Create a back-and-forth rank order: 1st, 16th, 2nd, 17th, 3rd, 18th, ...
standings_reset = standings.reset_index(drop=True)
n = len(standings_reset)
indices = []
for i in range(n // 2):
    indices.append(i)                 # front
    if i + n // 2 < n:
        indices.append(i + n // 2)    # back
# If odd number of teams, add last middle one
if n % 2 != 0:
    indices.append(n // 2)

overall_live_rank = {standings_reset.iloc[idx]['Team']: rnk + 1 for rnk, idx in enumerate(indices)}

ChasesTeams = ['Toronto Blue Jays', 'Seattle Mariners', 'Boston Red Sox', 'Baltimore Orioles', 'San Diego Padres', 'Kansas City Royals', 'Arizona Diamondbacks', 'Miami Marlins', 'Minnesota Twins', 'St. Louis Cardinals']
BrycesTeams = ['Los Angeles Dodgers', 'Philadelphia Phillies', 'Detroit Tigers', 'San Francisco Giants', 'Cleveland Guardians', 'Cincinnati Reds', 'Pittsburgh Pirates', 'Los Angeles Angels', 'Chicago White Sox', 'Colorado Rockies']
ZachsTeams = ['New York Yankees', 'New York Mets', 'Chicago Cubs', 'Atlanta Braves', 'Houston Astros', 'Milwaukee Brewers', 'Texas Rangers', 'Tampa Bay Rays', 'Athletics', 'Washington Nationals']

# Snake draft order: Bryce 1st, Zach 2nd, Chase 3rd. Team arrays are in pick order.
# R1: Bryce(1), Zach(2), Chase(3) | R2: Chase(4), Zach(5), Bryce(6) | R3: Bryce(7), ...
_bryce_ovr = [1,  6,  7, 12, 13, 18, 19, 24, 25, 30]
_zach_ovr  = [2,  5,  8, 11, 14, 17, 20, 23, 26, 29]
_chase_ovr = [3,  4,  9, 10, 15, 16, 21, 22, 27, 28]
draft_info = {}
for i, team in enumerate(BrycesTeams):
    ovr = _bryce_ovr[i]; draft_info[team] = {'rd': (ovr - 1) // 3 + 1, 'ovr': ovr}
for i, team in enumerate(ZachsTeams):
    ovr = _zach_ovr[i];  draft_info[team] = {'rd': (ovr - 1) // 3 + 1, 'ovr': ovr}
for i, team in enumerate(ChasesTeams):
    ovr = _chase_ovr[i]; draft_info[team] = {'rd': (ovr - 1) // 3 + 1, 'ovr': ovr}

# Process standings data
standings['W'] = standings['W'].astype(int)
standings['L'] = standings['L'].astype(int)
standings['PCT'] = standings['PCT'].astype(float)
standings = standings.sort_values(by='W', ascending=False).drop(columns=['PCT'])

chasesStandings = standings[standings['Team'].isin(ChasesTeams)].reset_index(drop=True)
chasesStandings.index += 1
brycesStandings = standings[standings['Team'].isin(BrycesTeams)].reset_index(drop=True)
brycesStandings.index += 1
zachsStandings = standings[standings['Team'].isin(ZachsTeams)].reset_index(drop=True)
zachsStandings.index += 1

teamToAbbr = {
    'Atlanta Braves': 'ATL', 'Texas Rangers': 'TEX', 'Chicago Cubs': 'CHC', 'San Diego Padres': 'SD', 'Seattle Mariners': 'SEA', 'Milwaukee Brewers': 'MIL', 'Tampa Bay Rays': 'TB', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH', 'Chicago White Sox': 'CHW',
    'New York Yankees': 'NYY', 'Philadelphia Phillies': 'PHI', 'Boston Red Sox': 'BOS', 'Detroit Tigers': 'DET', 'Kansas City Royals': 'KC', 'San Francisco Giants': 'SF', 'Cincinnati Reds': 'CIN', 'Los Angeles Angels': 'LAA', 'Athletics': 'ATH', 'Colorado Rockies': 'COL',
    'New York Mets': 'NYM', 'Los Angeles Dodgers': 'LAD', 'Houston Astros': 'HOU', 'Baltimore Orioles': 'BAL', 'Arizona Diamondbacks': 'ARI', 'Minnesota Twins': 'MIN', 'Cleveland Guardians': 'CLE', 'Pittsburgh Pirates': 'PIT', 'St. Louis Cardinals': 'STL', 'Miami Marlins': 'MIA'
}

chaseStandingsMobile = chasesStandings.copy()
bryceStandingsMobile = brycesStandings.copy()
zachStandingsMobile = zachsStandings.copy()

chaseStandingsMobile['Team'] = chaseStandingsMobile['Team'].map(teamToAbbr)
bryceStandingsMobile['Team'] = bryceStandingsMobile['Team'].map(teamToAbbr)
zachStandingsMobile['Team'] = zachStandingsMobile['Team'].map(teamToAbbr)

chaseStandingsMobile = chaseStandingsMobile[['Team', 'W']]
bryceStandingsMobile = bryceStandingsMobile[['Team', 'W']]
zachStandingsMobile = zachStandingsMobile[['Team', 'W']]

def build_combined_value_view_html(draft_info, overall_live_rank, teamToAbbr, ChasesTeams, BrycesTeams, ZachsTeams):
    owner_colors = {'Chase': '#2774AE', 'Bryce': '#57068c', 'Zach': '#e21833'}
    owner_map = {}
    for team in ChasesTeams: owner_map[team] = 'Chase'
    for team in BrycesTeams: owner_map[team] = 'Bryce'
    for team in ZachsTeams: owner_map[team] = 'Zach'

    rows = []
    for team in list(ChasesTeams) + list(BrycesTeams) + list(ZachsTeams):
        abbr = teamToAbbr.get(team, team)
        owner = owner_map.get(team, '')
        color = owner_colors.get(owner, '#999')
        d = draft_info.get(team, {})
        draft_ovr = d.get('ovr', 0)
        live_ovr = overall_live_rank.get(team, 0)
        delta = (live_ovr - draft_ovr) if (draft_ovr and live_ovr) else 0
        rows.append((abbr, owner, color, draft_ovr, live_ovr, delta))

    rows.sort(key=lambda x: x[4])  # default sort: current rank

    html = '<table class="standings-table" id="valueTable"><thead><tr>'
    html += '<th>TEAM</th>'
    html += '<th class="sortable" onclick="sortValueTable(1)">DRAFT &#8597;</th>'
    html += '<th class="sortable" onclick="sortValueTable(2)">CURR &#8597;</th>'
    html += '<th class="sortable" onclick="sortValueTable(3)">&#916; &#8597;</th>'
    html += '</tr></thead><tbody>'

    for abbr, owner, color, draft_ovr, live_ovr, delta in rows:
        if delta < 0:
            delta_html = f"<span style='color:#22c55e;font-weight:bold;'>&#9650;&nbsp;{abs(delta)}</span>"
        elif delta > 0:
            delta_html = f"<span style='color:#ef4444;font-weight:bold;'>&#9660;&nbsp;{delta}</span>"
        else:
            delta_html = "&#8212;"
        html += f'<tr data-owner="{owner}">'
        html += f'<td style="border-left:4px solid {color};font-weight:600;padding-left:12px;">{abbr}</td>'
        html += f'<td data-val="{draft_ovr}">{draft_ovr}</td>'
        html += f'<td data-val="{live_ovr}">{live_ovr}</td>'
        html += f'<td data-val="{delta}">{delta_html}</td>'
        html += '</tr>'

    html += '</tbody></table>'
    return html

combined_value_html = build_combined_value_view_html(draft_info, overall_live_rank, teamToAbbr, ChasesTeams, BrycesTeams, ZachsTeams)

# Calculate total wins and losses
chaseWins = chasesStandings['W'].sum()
bryceWins = brycesStandings['W'].sum()
zachWins = zachsStandings['W'].sum()

df = pd.read_excel('Wins_Over_Time.xlsx') 
# add on to end of dataframe with todays data and wins
target_day = date.today() - pd.Timedelta(days=1)
if pd.to_datetime(target_day) not in pd.to_datetime(df['Day']).values:
    todaysData = pd.DataFrame({'Day': [target_day], 'Chase': [chaseWins], 'Bryce': [bryceWins], 'Zach': [zachWins]})
    df = pd.concat([df, todaysData], ignore_index=True)
    df.to_excel('Wins_Over_Time.xlsx', index=False)
df.iloc[:, 1:] = df.iloc[:, 1:].sub(df.iloc[:, 1:].min(axis=1), axis=0)
# format dat as Oct-22
df['Day'] = pd.to_datetime(df['Day']).dt.strftime('%b-%d')

# Fetch today's and yesterday's schedule from the official MLB Stats API
_today = date.today()
_yesterday = _today - timedelta(days=1)

today_resp = requests.get(
    f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={_today.strftime("%Y-%m-%d")}'
)
today_data = today_resp.json()

# Fetch moneyline odds from The Odds API — keyed by (home_full_name, away_full_name)
odds_by_matchup = {}
ODDS_API_KEY = os.environ.get('ODDS_API_KEY', '')
if ODDS_API_KEY:
    odds_resp = requests.get(
        'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/',
        params={'apiKey': ODDS_API_KEY, 'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'american'}
    )
    if odds_resp.status_code == 200:
        for game in odds_resp.json():
            home_full = game['home_team']
            away_full = game['away_team']
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        prices = {o['name']: o['price'] for o in market['outcomes']}
                        home_price = prices.get(home_full)
                        away_price = prices.get(away_full)
                        if home_price is not None and away_price is not None:
                            if home_price < away_price:
                                fav_full, fav_price = home_full, home_price
                            else:
                                fav_full, fav_price = away_full, away_price
                            fav_abbr = teamToAbbr.get(fav_full, fav_full)
                            price_str = f"+{fav_price}" if fav_price > 0 else str(fav_price)
                            odds_by_matchup[(home_full, away_full)] = f"{fav_abbr} {price_str}"
                        break
                break

matchups = []
if today_data.get('dates'):
    for game in today_data['dates'][0]['games']:
        away_name = MLB_API_NAME_TO_FULL.get(game['teams']['away']['team']['name'], game['teams']['away']['team']['name'])
        home_name = MLB_API_NAME_TO_FULL.get(game['teams']['home']['team']['name'], game['teams']['home']['team']['name'])
        away_abbr = teamToAbbr.get(away_name, away_name).lower()
        home_abbr = teamToAbbr.get(home_name, home_name).lower()
        game_dt_utc = datetime.strptime(game['gameDate'], '%Y-%m-%dT%H:%M:%SZ')
        # Convert UTC to ET (UTC-4 during baseball season)
        game_dt_et = game_dt_utc - timedelta(hours=4)
        hour = game_dt_et.hour % 12 or 12
        game_time = f"{hour}:{game_dt_et.strftime('%M')} {'AM' if game_dt_et.hour < 12 else 'PM'} ET"
        matchups.append({
            'away_team': away_abbr,
            'home_team': home_abbr,
            'time': game_time,
            'odds': odds_by_matchup.get((home_name, away_name)),
        })

yesterday_resp = requests.get(
    f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={_yesterday.strftime("%Y-%m-%d")}&hydrate=linescore'
)
yesterday_data = yesterday_resp.json()

yesterday = []
if yesterday_data.get('dates'):
    for game in yesterday_data['dates'][0]['games']:
        if game.get('status', {}).get('detailedState') in ('Postponed', 'Cancelled'):
            continue
        away_name = MLB_API_NAME_TO_FULL.get(game['teams']['away']['team']['name'], game['teams']['away']['team']['name'])
        home_name = MLB_API_NAME_TO_FULL.get(game['teams']['home']['team']['name'], game['teams']['home']['team']['name'])
        away_abbr = teamToAbbr.get(away_name, away_name).lower()
        home_abbr = teamToAbbr.get(home_name, home_name).lower()
        home_score = game['teams']['home'].get('score', 0) or 0
        away_score = game['teams']['away'].get('score', 0) or 0
        if home_score > away_score:
            winner = home_abbr
            result = f"{home_abbr.upper()} {home_score}-{away_score}"
        else:
            winner = away_abbr
            result = f"{away_abbr.upper()} {away_score}-{home_score}"
        yesterday.append({
            'away_team': away_abbr,
            'home_team': home_abbr,
            'result': result,
            'winner': winner,
        })

# Create a DataFrame from the matchups list
matchups_df = pd.DataFrame(matchups)
dpt = generate_daily_projection_table(matchups_df, ChasesTeams, BrycesTeams, ZachsTeams, teamToAbbr)
html_table = "<table><thead><tr><th>Home Team</th><th>Away Team</th><th>Time</th><th>Odds</th></tr></thead><tbody>"
for i, row in matchups_df.iterrows():
    # if row['Home Team'] = ChasesTeams first row
    for team in ChasesTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            html_table += f"<td style='color:#2774AE'>{team}</td>"
    for team in BrycesTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            html_table += f"<td style='color:#57068c'>{team}</td>"
    for team in ZachsTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            html_table += f"<td style='color:#e21833'>{team}</td>"
    for team in ChasesTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            html_table += f"<td style='color:#2774AE'>{team}</td>"
    for team in BrycesTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            html_table += f"<td style='color:#57068c'>{team}</td>"
    for team in ZachsTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            html_table += f"<td style='color:#e21833'>{team}</td>"
    html_table += f"<td>{row['time']}</td><td>{row['odds']}</td></tr>"
html_table += "</tbody></table>"

# Create a DataFrame from the matchups list
yesterday_df = pd.DataFrame(yesterday)
html_table_yesterday = "<table><thead><tr><th>Home Team</th><th>Away Team</th><th>Result</th></tr></thead><tbody>"
for i, row in yesterday_df.iterrows():
    winner = row['winner']  
    for team in ChasesTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            if winner.lower() == row['home_team']:
                # make background #2774AE and font white
                html_table_yesterday += f"<td style='background-color:#2774AE;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#2774AE'>{team}</td>"
    for team in BrycesTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            if winner.lower() == row['home_team']:
                # make background #57068c and font white
                html_table_yesterday += f"<td style='background-color:#57068c;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#57068c'>{team}</td>"
    for team in ZachsTeams:
        team = teamToAbbr[team]
        if row['home_team'] == team.lower():
            if winner.lower() == row['home_team']:
                # make background #e21833 and font white
                html_table_yesterday += f"<td style='background-color:#e21833;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#e21833'>{team}</td>"
    for team in ChasesTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            if winner.lower() == row['away_team']:
                # make background #2774AE and font white
                html_table_yesterday += f"<td style='background-color:#2774AE;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#2774AE'>{team}</td>"
    for team in BrycesTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            if winner.lower() == row['away_team']:
                # make background #57068c and font white
                html_table_yesterday += f"<td style='background-color:#57068c;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#57068c'>{team}</td>"
    for team in ZachsTeams:
        team = teamToAbbr[team]
        if row['away_team'] == team.lower():
            if winner.lower() == row['away_team']:
                # make background #e21833 and font white
                html_table_yesterday += f"<td style='background-color:#e21833;color:white;'> <strong>{team}</strong></td>"
            else:
                html_table_yesterday += f"<td style='color:#e21833'>{team}</td>"         
    html_table_yesterday += f"<td>{row['result']}</td></tr>"
html_table_yesterday += "</tbody></table>"

# Generate HTML content
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Standings</title>
    <script >
        function openCity(evt, cityName) {{
        // Declare all variables
        var i, tabcontent, tablinks;

        // Get all elements with class="tabcontent" and hide them
        tabcontent = document.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {{
            tabcontent[i].style.display = "none";
        }}

        // Get all elements with class="tablinks" and remove the class "active"
        tablinks = document.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {{
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }}

        // Show the current tab, and add an "active" class to the button that opened the tab
        document.getElementById(cityName).style.display = "block";
        evt.currentTarget.className += " active";
    }}

    var _valueViewActive = false;
    function toggleValueView() {{
        _valueViewActive = !_valueViewActive;
        document.querySelectorAll('.toggle-btn').forEach(function(b) {{
            b.classList.toggle('active', _valueViewActive);
        }});
        document.getElementById('cardsRow').style.display = _valueViewActive ? 'none' : '';
        document.getElementById('valueViewSection').style.display = _valueViewActive ? 'block' : 'none';
    }}

    var _sortCol = 2;
    var _sortAsc = true;

    function sortValueTable(col) {{
        if (_sortCol === col) {{
            _sortAsc = !_sortAsc;
        }} else {{
            _sortCol = col;
            _sortAsc = true;
        }}
        var tbody = document.querySelector('#valueTable tbody');
        var rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort(function(a, b) {{
            var aVal = parseFloat(a.cells[col].dataset.val);
            var bVal = parseFloat(b.cells[col].dataset.val);
            return _sortAsc ? aVal - bVal : bVal - aVal;
        }});
        rows.forEach(function(r) {{ tbody.appendChild(r); }});
    }}

    function filterOwner(btn, owner) {{
        document.querySelectorAll('.vf-btn').forEach(function(b) {{ b.classList.remove('active'); }});
        btn.classList.add('active');
        document.querySelectorAll('#valueTable tbody tr').forEach(function(r) {{
            r.style.display = (owner === 'all' || r.dataset.owner === owner) ? '' : 'none';
        }});
    }}
    </script>
    <style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}

    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #77B5FE 0%, #4d94e8 100%);
        min-height: 100vh;
        padding: 20px;
    }}

    h1 {{
        text-align: center;
        color: #ffffff;
        font-size: 48px;
        margin: 20px 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        font-weight: 700;
        letter-spacing: 2px;
    }}

    h2 {{
        color: #333;
        font-weight: 600;
    }}

    h3 {{
        color: #555;
        font-size: 28px;
        margin: 20px 0 15px 0;
        font-weight: 600;
    }}

    table {{
        margin: 0 auto;
        width: 100%;
        border-collapse: collapse;
        background: white;
        border-radius: 8px;
        overflow: hidden;
    }}

    th, td {{
        padding: 14px 16px;
        text-align: center;
        font-size: 16px;
    }}

    th {{
        background: linear-gradient(135deg, #7B77FE 0%, #5450d4 100%);
        color: white;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 14px;
        letter-spacing: 1px;
    }}

    td {{
        border-bottom: 1px solid #f0f0f0;
    }}

    img {{
        display: block;
        margin: 0 auto;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        height: 120px;
        width: auto;
    }}

    .row {{
        display: flex;
        justify-content: space-around;
        margin-top: 30px;
        gap: 20px;
        max-width: 1400px;
        margin-left: auto;
        margin-right: auto;
    }}

    .column {{
        flex: 1;
        padding: 0;
        min-width: 0;
    }}

    .card {{
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        padding: 30px;
        text-align: center;
        height: 100%;
    }}

    .card-header {{
        margin-bottom: 20px;
    }}

    .card-body h2 {{
        font-size: 32px;
        color: #333;
        margin: 15px 0;
        font-weight: 700;
    }}

    .table-container {{
        margin-top: 20px;
        overflow-x: auto;
        border-radius: 8px;
    }}

    .table-container2 {{
        margin-top: 0px;
        overflow-x: visible;
        font-size: 12px;
    }}

    .table-container table,
    .table-container2 table {{
        border-radius: 8px;
        overflow: hidden;
    }}

    #myLineChart {{
        width: 100%;
        max-width: 600px;
        margin: 20px auto;
    }}

    .progress-container {{
        width: 100%;
        max-width: 1400px;
        margin: 0 auto 20px auto;
        background-color: rgba(255, 255, 255, 0.3);
        border-radius: 50px;
        position: relative;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}

    .progress-bar {{
        height: 40px;
        background: linear-gradient(90deg, #7B77FE 0%, #5450d4 100%);
        text-align: center;
        color: white;
        line-height: 40px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 16px;
        transition: width 0.5s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }}

    .tab {{
        overflow: hidden;
        background: white;
        text-align: center;
        max-width: 1400px;
        margin: 30px auto;
        border-radius: 50px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        padding: 5px;
    }}

    .tab button {{
        background-color: transparent;
        border: none;
        outline: none;
        cursor: pointer;
        padding: 14px 30px;
        transition: all 0.3s;
        font-size: 16px;
        font-weight: 600;
        color: #666;
        border-radius: 50px;
        margin: 0 5px;
    }}

    .tab button:hover {{
        background: linear-gradient(135deg, #7B77FE 0%, #5450d4 100%);
        color: white;
    }}

    .tab button.active {{
        background: linear-gradient(135deg, #7B77FE 0%, #5450d4 100%);
        color: white;
        box-shadow: 0 3px 10px rgba(119, 181, 254, 0.4);
    }}

    .tabcontent {{
        display: none;
        padding: 30px;
        background: white;
        border-radius: 20px;
        max-width: 1400px;
        margin: 20px auto;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }}

    .tabcontent h2 {{
        color: #333;
        margin-bottom: 20px;
        font-weight: 700;
    }}

    hr {{
        border: none;
        height: 3px;
        background: linear-gradient(90deg, transparent, currentColor, transparent);
        margin: 15px 0;
    }}

    .standings-table {{
        background: white;
        border-radius: 12px;
        overflow: hidden;
        margin: 20px auto;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }}

    .standings-table th {{
        background: linear-gradient(135deg, #7B77FE 0%, #5450d4 100%);
        padding: 14px 16px;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: white;
    }}

    .standings-table td {{
        padding: 14px 16px;
        font-weight: 600;
        font-size: 16px;
    }}

    .daily-overview-title {{
        color: white;
        padding: 5px;
        text-align: center;
        margin: 5px auto;
        max-width: 1400px;
        font-weight: 700;
    }}

    @media screen and (max-width: 600px) {{
        .column {{
            flex: 1;
            padding: 3px;
            min-width: 0;
        }}

        .row {{
            flex-direction: row;
            gap: 3px;
            margin-top: 15px;
        }}

        .table-container {{
            display: none;
        }}

        .table-container2 {{
            display: block;
        }}

        .table-container2 table {{
            font-size: 12px;
        }}

        .table-container2 th,
        .table-container2 td {{
            padding: 8px 4px;
        }}

        .table-container2 th {{
            font-size: 11px;
        }}

        h1 {{
            font-size: 28px;
            margin: 10px 0;
            letter-spacing: 1px;
        }}

        .card {{
            padding: 10px;
            border-radius: 12px;
        }}

        .card-body h2 {{
            font-size: 20px;
            margin: 8px 0;
            font-weight: 700;
        }}

        .card-header {{
            margin-bottom: 10px;
        }}

        .card-header img {{
            height: 90px;
            width: auto;
        }}

        hr {{
            margin: 8px 0;
            height: 2px;
        }}

        .tab button {{
            padding: 10px 15px;
            font-size: 13px;
        }}

        body {{
            padding: 8px;
        }}

        .progress-bar {{
            height: 32px;
            line-height: 32px;
            font-size: 13px;
        }}

        .progress-container {{
            margin-bottom: 15px;
        }}

        .tabcontent {{
            padding: 15px;
        }}

        tr:hover td {{
            background-color: transparent;
        }}

        .daily-overview-title {{
            font-size: 20px;
            margin: 10px auto;
        }}

        .standings-table {{
            font-size: 14px;
        }}

        .standings-table th {{
            font-size: 12px;
            padding: 10px 5px;
        }}

        .standings-table td {{
            font-size: 14px;
            padding: 8px 4px;
        }}
    }}

    @media screen and (min-width: 601px) {{
        .table-container2 {{
            display: none;
        }}
        #chart-container {{
            display: none;
        }}
    }}

    ch {{
        text-decoration: underline;
        -webkit-text-decoration-color: red;
        text-decoration-color: red;
        font-size: 24px;
        font-weight: bold;
    }}

    /* Chart container styling */
    #chart-container {{
        background: white;
        border-radius: 20px;
        padding: 10px;
        margin: 10px auto;
        max-width: 95%;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }}

    .title-row {{
        display: flex;
        align-items: center;
        justify-content: center;
        max-width: 1400px;
        margin: 20px auto;
        position: relative;
    }}

    .title-row h1 {{
        margin: 0;
    }}

    .toggle-btn {{
        position: absolute;
        right: 0;
        background: rgba(255,255,255,0.2);
        border: 2px solid rgba(255,255,255,0.6);
        color: white;
        padding: 8px 18px;
        border-radius: 50px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        backdrop-filter: blur(5px);
        white-space: nowrap;
    }}

    .toggle-btn:hover {{
        background: rgba(255,255,255,0.35);
    }}

    .toggle-btn.active {{
        background: white;
        color: #4d94e8;
        border-color: white;
    }}

    #valueViewSection {{
        display: none;
        max-width: 600px;
        margin: 20px auto;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        padding: 20px;
    }}

    .value-filter {{
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }}

    .vf-btn {{
        background: transparent;
        border: 2px solid #ddd;
        padding: 6px 18px;
        border-radius: 50px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        color: #666;
    }}

    .vf-btn.active, .vf-btn:hover {{
        background: linear-gradient(135deg, #7B77FE 0%, #5450d4 100%) !important;
        color: white !important;
        border-color: transparent !important;
    }}

    .sortable {{
        cursor: pointer;
    }}

    .sortable:hover {{
        opacity: 0.8;
    }}

    @media screen and (max-width: 600px) {{
        #valueViewSection {{
            max-width: 100%;
            padding: 12px;
            border-radius: 12px;
        }}
    }}

    .desktop-vv {{ display: inline-block; }}
    .mobile-vv  {{ display: none; }}

    @media screen and (max-width: 600px) {{
        .toggle-btn {{
            padding: 6px 10px;
            font-size: 11px;
        }}
        .desktop-vv {{ display: none; }}
        .mobile-vv  {{
            display: block;
            position: static;
            width: fit-content;
            margin: 14px auto;
        }}
    }}

</style>

</head>
<body>

    <div class="progress-container">
        <div class="progress-bar" id="progressBar">0/0</div>
    </div>

    <script>
        let x = {chaseWins+ bryceWins + zachWins}
        let y = {2430}
        let percentage = ((x / y) * 100).toFixed(1);

        let progressBar = document.getElementById("progressBar");
        progressBar.style.width = percentage + "%";
        progressBar.innerText = percentage+ "%";
    </script>

<div class="title-row">
    <h1>MLB Palooza</h1>
    <button id="valueViewBtn" class="toggle-btn desktop-vv" onclick="toggleValueView()">Value View</button>
</div>
<div id="chart-container">
    <canvas id="myLineChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    console.log('Creating chart...');
    var ctx = document.getElementById('myLineChart').getContext('2d');
    
    const myLineChart = new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: {df['Day'].to_list()},
            datasets: [{{
                label: 'Chase',
                data: {df['Chase'].to_list()},
                fill: false,
                borderColor: '#2774AE',
                tension: 0.1,
                pointRadius: 0
            }},
            {{
                label: 'Bryce',
                data: {df['Bryce'].to_list()},
                fill: false,
                borderColor: '#57068c',
                tension: 0.1,
                pointRadius: 0
            }},
            {{
                label: 'Zach',
                data: {df['Zach'].to_list()},
                fill: false,
                borderColor: '#e21833',
                tension: 0.1,
                pointRadius: 0
            }}]
        }},
    
        options: {{
            responsive: false,
            scales: {{
                y: {{
                    beginAtZero: true,
                    grid: {{
                        display: false // Hide y-axis gridlines
                    }},
                    title: {{
                        display: false, // Show y-axis title
                    }}                
                }},
                x: {{
                    grid: {{
                        display: false // Hide x-axis gridlines
                    }}
                }}
            }},
            plugins: {{
                legend: {{
                    display: false,
                    position: 'left',
                    fullSize: false,
                }},
                title: {{
                    display: true,
                    text: 'Wins Margin',
                    font: {{
                        size: 15
                    }},
                    align: 'start',
                    color: 'black'
                }},
            }}
        }}
    }});
</script>
<button id="valueViewBtnM" class="toggle-btn mobile-vv" onclick="toggleValueView()">Value View</button>

<div class="row" id="cardsRow">
    <div class="column">
        <div class="card">
            <div class="card-header">
                {img_to_html('photos/ChaseHead.png')}
                <hr style="background: #2774AE; background-image: none; height: 3px; border: none; margin: 15px 0;"/>
            </div>
            <div class="card-body">
                <h2>Chase's Wins: <br>{chaseWins}</h2>
                <div class="table-container">
                    {chasesStandings.to_html(index=False)}
                </div>
                <div class="table-container2">
                    {chaseStandingsMobile.to_html(index=False)}
                </div>
            </div>
        </div>
    </div>

    <div class="column">
        <div class="card">
            <div class="card-header">
                {img_to_html('photos/BryceHead.png')}
                <hr style="background: #57068c; background-image: none; height: 3px; border: none; margin: 15px 0;"/>
            </div>
            <div class="card-body">
                <h2>Bryce's Wins: <br>{bryceWins}</h2>
                <div class="table-container">
                    {brycesStandings.to_html(index=False)}
                </div>
                <div class="table-container2">
                    {bryceStandingsMobile.to_html(index=False)}
                </div>
            </div>
        </div>
    </div>

    <div class="column">
        <div class="card">
            <div class="card-header">
                {img_to_html('photos/ZachHead.png')}
                <hr style="background: #e21833; background-image: none; height: 3px; border: none; margin: 15px 0;"/>
            </div>
            <div class="card-body">
                <h2>Zach's Wins: <br>{zachWins}</h2>
                <div class="table-container">
                    {zachsStandings.to_html(index=False)}
                </div>
                <div class="table-container2">
                    {zachStandingsMobile.to_html(index=False)}
                </div>
            </div>
        </div>
    </div>
</div>

<div id="valueViewSection">
    <div class="value-filter">
        <button class="vf-btn active" data-owner="all" onclick="filterOwner(this, 'all')">All</button>
        <button class="vf-btn" data-owner="Chase" onclick="filterOwner(this, 'Chase')" style="border-color:#2774AE;color:#2774AE;">Chase</button>
        <button class="vf-btn" data-owner="Bryce" onclick="filterOwner(this, 'Bryce')" style="border-color:#57068c;color:#57068c;">Bryce</button>
        <button class="vf-btn" data-owner="Zach" onclick="filterOwner(this, 'Zach')" style="border-color:#e21833;color:#e21833;">Zach</button>
    </div>
    {combined_value_html}
</div>

<div class="tab">
  <button class="tablinks" onclick="openCity(event, 'TG')">Today's Games</button>
  <button class="tablinks" onclick="openCity(event, 'YG')">Yesterday's Games</button>
</div>


<div id="TG" class="tabcontent">
    <h2 style="text-align: center;">Today's Games</h2>
    {html_table}
</div>

<div id="YG" class="tabcontent">
  <h2 style="text-align: center;">Yesterday's Games</h2>
  {html_table_yesterday}
</div>

</body>
</html>
"""

html_content += dpt

# Write HTML content to a file
with open('index.html', 'w') as f:
    f.write(html_content)

print("HTML file generated: index.html")