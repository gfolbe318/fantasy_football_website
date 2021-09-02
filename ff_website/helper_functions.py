from ff_website.constants import PLAYOFFS, SEASON
from numpy import add, dtype
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

    return series_winner, series_split, series_loser_wins == series_winner_wins


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


def get_league_members(query):
    names = set()
    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        names.add(team_A_name)
        names.add(team_B_name)
    return list(names)


def get_standings(query):
    league_members = get_league_members(query)

    df = pd.DataFrame(
        columns=["Wins", "Losses", "PF", "PA"],
        index=league_members
    ).fillna(0.0)

    for row in query:
        team_A_score = row["team_A_score"]
        team_B_score = row["team_B_score"]

        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        winning_team = team_A_name if team_A_score > team_B_score else team_B_name

        if not row["playoffs"]:
            df.at[team_A_name, "PF"] += team_A_score
            df.at[team_A_name, "PA"] += team_B_score

            df.at[team_B_name, "PF"] += team_B_score
            df.at[team_B_name, "PA"] += team_A_score

            if winning_team == team_A_name:
                df.at[team_A_name, "Wins"] += 1
                df.at[team_B_name, "Losses"] += 1

            else:
                df.at[team_B_name, "Wins"] += 1
                df.at[team_A_name, "Losses"] += 1

    df = df.sort_values(["Wins", "PF"], ascending=False)
    df["Wins"] = df["Wins"].astype("int64")
    df["Losses"] = df["Losses"].astype("int64")

    ranks = {}
    i = 1
    for index, row in df.iterrows():
        ranks[index] = i
        i += 1

    return df, ranks


def get_playoffs(query, ranks):

    playoff_weeks = {}
    for row in query:
        if row["playoffs"] == 1:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]

            team_A_name_key = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name_key = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            team_A_rank = ranks[team_A_name_key]
            team_B_rank = ranks[team_B_name_key]

            f"{team_A_rank} {team_A_name_key}"
            team_B_for_df = f"{ranks[team_B_name_key]} {team_B_name_key}"

    print(playoff_weeks)


def get_overall_record(query, name):
    wins, losses, po_wins, po_losses = 0, 0, 0, 0

    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        team_A_score = float(row["team_A_score"])
        team_B_score = float(row["team_B_score"])

        if team_A_name == name and team_A_score > team_B_score:
            wins += 1
            if row["playoffs"] == 1:
                po_wins += 1

        elif team_B_name == name and team_B_score > team_A_score:
            wins += 1
            if row["playoffs"] == 1:
                po_wins += 1

        elif team_A_name == name and team_A_score < team_B_score:
            losses += 1
            if row["playoffs"] == 1:
                po_losses += 1

        elif team_B_name == name and team_B_score < team_A_score:
            losses += 1
            if row["playoffs"] == 1:
                po_losses += 1

    return f"{wins}-{losses}", f"{po_wins}-{po_losses}"


def get_additional_stats(query, name):
    longest_win_streak, current_win_streak = 0, 0
    longest_losing_streak, current_losing_streak = 0, 0
    total_points = 0.0
    most_points, fewest_points = 0.0, 1000

    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        team_A_score = float(row["team_A_score"])
        team_B_score = float(row["team_B_score"])

        if team_A_name == name and team_A_score > team_B_score:
            total_points += team_A_score
            current_win_streak += 1
            if current_losing_streak > longest_losing_streak:
                longest_losing_streak = current_losing_streak
            current_losing_streak = 0
            if team_A_score > most_points:
                most_points = team_A_score
            if team_A_score < fewest_points:
                fewest_points = team_A_score

        elif team_B_name == name and team_B_score > team_A_score:
            total_points += team_B_score
            current_win_streak += 1
            if current_losing_streak > longest_losing_streak:
                longest_losing_streak = current_losing_streak
            current_losing_streak = 0
            if team_B_score > most_points:
                most_points = team_B_score
            if team_B_score < fewest_points:
                fewest_points = team_B_score

        elif team_A_name == name and team_A_score < team_B_score:
            total_points += team_A_score
            current_losing_streak += 1
            if current_win_streak > longest_win_streak:
                longest_win_streak = current_win_streak
            current_win_streak = 0
            if team_A_score > most_points:
                most_points = team_A_score
            if team_A_score < fewest_points:
                fewest_points = team_A_score

        elif team_B_name == name and team_B_score < team_A_score:
            total_points += team_B_score
            current_losing_streak += 1
            if current_win_streak > longest_win_streak:
                longest_win_streak = current_win_streak
            current_win_streak = 0
            if team_B_score > most_points:
                most_points = team_B_score
            if team_B_score < fewest_points:
                fewest_points = team_B_score

    if current_win_streak > longest_win_streak:
        longest_win_streak = current_win_streak
    if current_losing_streak > longest_losing_streak:
        longest_losing_streak = current_losing_streak

    return total_points, longest_win_streak, longest_losing_streak, most_points, fewest_points


def get_playoff_appearances(query):
    playoffs = set()
    for row in query:
        if row[PLAYOFFS] == 1:
            playoffs.add(row[SEASON])

    l = list(playoffs)
    if len(l) == 0:
        return "None"
    else:
        ret = f"{len(l)} ("
        for index, year in enumerate(l):
            ret += str(year)
            if index != len(l) - 1:
                ret += ", "
        ret += ")"
        return ret


def highlight_winning_rows(s):
    if s["Result"] == "Win":
        return ['background-color: #ccffcc']*5
    else:
        return ['background-color: #ffcccc']*5


def get_individual_schedule(query, name):
    df = pd.DataFrame(
        columns=["Format", "Opponent", "Result", "Score", "Record"])
    score, result, format, opponent = None, None, None, None
    wins, losses = 0, 0

    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        team_A_score = float(row["team_A_score"])
        team_B_score = float(row["team_B_score"])

        if team_A_score > team_B_score:
            score = f"{team_A_score}-{team_B_score}"
        else:
            score = f"{team_B_score}-{team_A_score}"

        if team_A_name == name and team_A_score > team_B_score:
            result = "Win"
            wins += 1

        elif team_B_name == name and team_B_score > team_A_score:
            result = "Win"
            wins += 1

        elif team_A_name == name and team_A_score < team_B_score:
            result = "Loss"
            losses += 1
        elif team_B_name == name and team_B_score < team_A_score:
            result = "Loss"
            losses += 1

        if row[PLAYOFFS] == 1:
            format = "Playoffs"
        else:
            format = "Regular Season"

        if team_A_name == name:
            opponent = team_B_name
        else:
            opponent = team_A_name

        record = f"{wins}-{losses}"

        df.loc[len(df.index)] = [format, opponent, result, score, record]

    df.index += 1

    return df


def get_schedules(query, name):
    split_queries = {}
    for row in query:
        year = row[SEASON]
        if year not in split_queries:
            split_queries[year] = [row]
        else:
            split_queries[year].append(row)

    all_schedules = {}

    for key, value in split_queries.items():
        df = get_individual_schedule(value, name)
        styled = df.style.apply(highlight_winning_rows, 1)

        all_schedules[key] = styled.render()

    return all_schedules
