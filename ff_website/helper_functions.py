import pandas as pd


def get_series_split(df: pd.DataFrame):
    winners = df["Winning Team"].value_counts(ascending=False)
    series_winner = winners.index[0]
    if len(winners.index) > 1:
        series_loser = winners.index[1]
    else:
        series_loser = df.at[0, "Losing Team"]

    series_winner_wins = winners[series_winner]
    series_loser_wins = 0 if len(
        winners.index) == 1 else winners[series_loser]
    series_split = f"{series_winner_wins}-{series_loser_wins}"

    return series_winner, series_split


def get_matchup_breakdown(df: pd.DataFrame):
    split = df["Matchup Format"].value_counts()
    if "Regular Season" in split.index:
        num_regular_season = split["Regular Season"]
    else:
        num_regular_season = 0

    if "Playoffs" in split.index:
        num_playoff = split["Playoffs"]
    else:
        num_playoff = 0

    return num_regular_season, num_playoff


def get_streak_head_to_head(df: pd.DataFrame):
    streak_holder = df.at[len(df.index) - 1, "Winning Team"]
    streak_count = 1

    for i in range(len(df.index) - 2, -1, -1):
        if df.at[i, "Winning Team"] != streak_holder:
            break
        else:
            streak_count += 1

    return streak_holder, streak_count
