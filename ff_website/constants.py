league_IDs = {
    "2018": "143059",
    "2019": "50890012",
    "2020": "50890012"
}

CURRENT_SEASON = 2021

# db keys
MEMBER_ID = "member_id"
FIRST_NAME = "first_name"
LAST_NAME = "last_name"
YEAR_JOINED = "year_joined"
ACTIVE = "active"
IMG_FILEPATH = "img_filepath"
GAME_ID = "game_id"
TEAM_A_SCORE = "team_A_score"
TEAM_B_SCORE = "team_B_score"
SEASON = "season"
WEEK = "week"
MATCHUP_LENGTH = "matchup_length"
PLAYOFFS = "playoffs"
TEAM_A_ID = "team_A_id"
TEAM_B_ID = "team_B_id"
USER_ID = "user_id"
USERNAME = "username"
EMAIL = "email"
PASSWORD = "password"

# Additional JSON keys
SEASON = "season"
HOME_TEAM = "home_team"
HOME_SCORE = "home_score"
AWAY_TEAM = "away_team"
AWAY_SCORE = "away_score"


member_data = "ff_website\data\\all_members.json"
games_data = "ff_website\data\\all_games.json"

CURRENT_SEASON_CARDS = [
    {
        "name": "Standings",
        "filename": 'img/standings.png',
        "description": "View the current standings, roto, and playoff picture",
        "link": 'current_season_standings'
    },
    {
        "name": "Payouts",
        "filename": 'img/payouts.png',
        "description": "See how the league pot is being divided",
        "link": 'current_season_payouts'
    },
    {
        "name": "Analytics",
        "filename": 'img/analytics.png',
        "description": "Take a closer look at how your team compares to the rest",
        "link": 'current_season_analytics'
    },
    {
        "name": "Report of The Week",
        "filename": 'img/report.png',
        "description": "Coming to you live from Lincoln, it's Jart's Report of the Week",
        "link": 'current_season_standings'
    },
    {
        "name": "Power Rankings",
        "filename": 'img/power_rankings.png',
        "description": "Unofficial official rankings",
        "link": 'current_season_power_rankings'
    },
    {
        "name": "Announcements",
        "filename": 'img/announcements.png',
        "description": "Announcements from the comissioner as well as for the website",
        "link": 'current_season_standings'
    }
]
