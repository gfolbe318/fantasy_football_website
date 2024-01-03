league_IDs = {
    "2017": "237841",
    "2018": "143059",
    "2019": "50890012",
    "2020": "50890012",
    "2021": "50890012",
    "2022": "50890012",
    "2023": "50890012",
}

CURRENT_SEASON = 2023

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
ADMIN_PRIVILEGES = "admin_privileges"
ANNOUNCEMENT_PRIVILEGES = "announcement_privileges"

ANNOUNCEMENT_ID = "announcement_id"
AUTHOR = "author"
TITLE = "title"
ANNOUNCEMENT = "announcement"
TIMESTAMP = "timestamp"

# Additional JSON keys
SEASON = "season"
HOME_TEAM = "home_team"
HOME_SCORE = "home_score"
AWAY_TEAM = "away_team"
AWAY_SCORE = "away_score"
STATIC_URL = "static_url"


member_data = "all_members.json"
games_data = "all_games.json"

NUM_PLAYOFF_TEAMS_PER_YEAR = {
    2017: 4,
    2018: 6,
    2019: 6,
    2020: 6,
    2021: 6,
    2022: 6,
    2023: 6
}

CURRENT_SEASON_CARDS = [
    {
        "name": "Season Info",
        "filename": 'img/standings.png',
        "description": "View the current standings, roto, playoff picture, and this year's results",
        "link": 'current_season_info'
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
        "description": "Coming to you live from Omaha, it's the Jart Report🌽!",
        "link": 'current_season_report'
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
        "link": 'current_season_announcements'
    }
]
