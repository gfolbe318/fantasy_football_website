import json
import requests

from credentials import cookies

from ff_website.constants import league_IDs


league_members = json.load(open("data\\member_ids.json"))


def load_notebook(year):
    ID = league_IDs[year]

    base_url = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{ID}"
    r = requests.get(url=base_url,
                     params={"view": "mMatchupScore"},
                     cookies=cookies)
    d = r.json()
    return d


def get_data_one_week_playoffs(year):
    d = load_notebook(year)
    all_games = []

    member_ids = league_members[year]

    for game in d["schedule"]:
        if game["playoffTierType"] == "WINNERS_BRACKET" \
                or game["playoffTierType"] == "NONE":
            week = game["matchupPeriodId"]

            home_team_member = member_ids[str(game["home"]["teamId"])]
            home_score = game["home"]["totalPoints"]

            # Account for bye weeks
            if "away" in game:
                away_team_member = member_ids[str(game["away"]["teamId"])]
                away_score = game["away"]["totalPoints"]

            playoffs = False if game["playoffTierType"] == "NONE" else True

            all_games.append(
                {"season": year,
                 "week": week,
                 "matchup_length": 1,
                 "playoffs": playoffs,
                 "home_team": home_team_member,
                 "home_score": home_score,
                 "away_team": away_team_member,
                 "away_score": away_score
                 }
            )

    return all_games


def get_data_multiple_week_playoffs(year):
    # TODO: For now this is fine, but it might be necessary to implement later
    pass


def get_all_data():
    all_games = []

    games2017 = json.load(open("data\\2017games.json", "r"))
    for game in games2017:
        all_games.append(game)

    for year in ["2018", "2019", "2020"]:
        data = get_data_one_week_playoffs(year)
        json.dump(data, open(f"data\\{year}games.json", "w"), indent=4)
        for game in data:
            all_games.append(game)

    json.dump(all_games, open("data\\all_games.json", "w"))


if __name__ == "__main__":
    get_all_data()
