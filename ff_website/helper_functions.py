from logging import lastResort
from ff_website.constants import *
import pandas as pd
import os
import json
from collections import OrderedDict
import heapq


class Record(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.name}: {self.value}"

    def __lt__(self, other):
        return self.value > other.value


def jsonify_members(query):
    data = [
        {
            MEMBER_ID: i[MEMBER_ID],
            FIRST_NAME: i[FIRST_NAME],
            LAST_NAME: i[LAST_NAME],
            YEAR_JOINED: i[YEAR_JOINED],
            ACTIVE: i[ACTIVE],
            IMG_FILEPATH: i[IMG_FILEPATH]

        } for i in query
    ]

    return data


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


def get_playoffs(query):
    playoffs = {}
    _, ranks = get_standings(query)
    for row in query:
        if row[PLAYOFFS] == 1:
            week = row[WEEK]

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            team_A_score = row[TEAM_A_SCORE]
            team_B_score = row[TEAM_B_SCORE]

            if team_A_score > team_B_score:
                winning_team = team_A_name
                winning_score = team_A_score
                winning_seed = ranks[team_A_name]
                losing_team = team_B_name
                losing_score = team_B_score
                losing_seed = ranks[team_B_name]

            else:
                winning_team = team_B_name
                winning_score = team_B_score
                winning_seed = ranks[team_B_name]

                losing_team = team_A_name
                losing_score = team_A_score
                losing_seed = ranks[team_A_name]

            if week not in playoffs:
                playoffs[week] = [{
                    "winning_team": winning_team,
                    "winning_score": winning_score,
                    "winning_seed": winning_seed,
                    "losing_team": losing_team,
                    "losing_score": losing_score,
                    "losing_seed": losing_seed
                }]
            else:
                playoffs[week].append({
                    "winning_team": winning_team,
                    "winning_score": winning_score,
                    "winning_seed": winning_seed,
                    "losing_team": losing_team,
                    "losing_score": losing_score,
                    "losing_seed": losing_seed
                })
    return playoffs


def get_league_members(query):
    names = set()
    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        names.add(team_A_name)
        names.add(team_B_name)
    names_list = list(names)
    names_list.sort()
    return names_list


def get_standings(query, include_playoffs=False):
    league_members = get_league_members(query)

    df = pd.DataFrame(
        columns=["Wins", "Losses", "PF", "PA"],
        index=league_members
    ).fillna(0.0)

    if not include_playoffs:
        query = [x for x in query if x[PLAYOFFS] == 0]

    for row in query:
        team_A_score = row["team_A_score"]
        team_B_score = row["team_B_score"]

        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        winning_team = team_A_name if team_A_score > team_B_score else team_B_name

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

    return f"{wins}-{losses}", f"{po_wins}-{po_losses}", wins, losses, po_wins, po_losses


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

    return round(total_points, 2), longest_win_streak, longest_losing_streak, most_points, fewest_points


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


def get_rank_of_team(standings, name):
    counter = 1
    for index, _ in standings.iterrows():
        if index == name:
            return counter
        counter += 1
    return counter


def ordinal(n):
    return "%d%s" % (n, "tsnrhtdd"[(n//10 % 10 != 1)*(n % 10 < 4)*n % 10::4])


def get_playoff_finish(playoffs, standings, name):
    rank = ordinal(get_rank_of_team(standings, name))

    num_rounds = len(playoffs)

    finish = "DNQ"
    round = 1
    for _, results in playoffs.items():
        for game in results:
            if game["losing_team"] == name and round == 1 and num_rounds == 3:
                finish = "Quarterfinals"
            elif game["losing_team"] == name and round == 1 and num_rounds == 2:
                finish = "Semifinals"

            elif game["losing_team"] == name and round == 2 and num_rounds == 3:
                finish = "Semifinals"

            elif game["losing_team"] == name and round == 2 and num_rounds == 2:
                finish = "Runner up"

            elif game["losing_team"] == name and round == 3 and num_rounds == 3:
                finish = "Runner up"

            elif game["winning_team"] == name and round == 2 and num_rounds == 2:
                finish = "Champion"

            elif game["winning_team"] == name and round == 3 and num_rounds == 3:
                finish = "Champion"

        round += 1

    return rank, finish


def get_summaries(query, name):
    split_queries = {}
    for row in query:
        year = row[SEASON]
        if year not in split_queries:
            split_queries[year] = [row]
        else:
            split_queries[year].append(row)

    all_seasons = {}
    all_playoffs = {}

    for key, value in split_queries.items():
        df, _ = get_standings(value)
        playoffs = get_playoffs(value)
        all_seasons[key] = df
        all_playoffs[key] = playoffs

    df = pd.DataFrame(columns=["Record", "TPF",
                               "TPA", "Playoffs", "Overall Finish"])

    final_record, tpf, tpa, playoffs, over_finish = None, None, None, None, None
    for (year, standings), (_, playoffs) in zip(all_seasons.items(), all_playoffs.items()):
        if name in standings.index.to_list():
            wins = standings.at[name, "Wins"]
            losses = standings.at[name, "Losses"]
            final_record = f"{wins}-{losses}"
            tpf = standings.at[name, "PF"]
            tpa = standings.at[name, "PA"]
            rank, finish = get_playoff_finish(
                playoffs, standings, name)
            if year == CURRENT_SEASON:
                over_finish = "--"
                playoffs = "--"
            else:
                if finish == "DNQ":
                    playoffs = "No"
                    over_finish = rank
                else:
                    playoffs = "Yes"
                    over_finish = finish

            df.loc[year] = [final_record, tpf, tpa, playoffs, over_finish]

    return df


def get_championships(summaries: pd.DataFrame, name):
    championships = []
    if name == "Garrett Folbe":
        championships.append(2015)
    if name == "Jonah Lopas":
        championships.append(2016)
    for index, row in summaries.iterrows():
        if row["Overall Finish"] == "Champion":
            championships.append(index)

    if len(championships) == 0:
        return "None"
    else:
        ret = f"{len(championships)} ("
        for index, year in enumerate(championships):
            ret += str(year)
            if index != len(championships) - 1:
                ret += ", "
        ret += ")"
        return ret


def get_week_results(query, running_games):
    df = pd.DataFrame(columns=["Winning Team", "Losing Team", "Score"])
    standings, _ = get_standings(running_games)
    for row in query:
        winning_team, losing_team, score = None, None, None

        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_A_score = float(row["team_A_score"])
        team_A_wins = standings.at[team_A_name, "Wins"]
        team_A_losses = standings.at[team_A_name, "Losses"]
        team_A_record = f"({team_A_wins}-{team_A_losses})"

        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        team_B_score = float(row["team_B_score"])
        team_B_wins = standings.at[team_B_name, "Wins"]
        team_B_losses = standings.at[team_B_name, "Losses"]
        team_B_record = f"({team_B_wins}-{team_B_losses})"

        if team_A_score > team_B_score:
            winning_team = f"{team_A_name} {team_A_record}"
            losing_team = f"{team_B_name} {team_B_record}"
            score = f"{team_A_score}-{team_B_score}"
        else:
            winning_team = f"{team_B_name} {team_B_record}"
            losing_team = f"{team_A_name} {team_A_record}"
            score = f"{team_B_score}-{team_A_score}"

        df.loc[len(df.index)] = [winning_team, losing_team, score]
    df.index += 1
    return df


def get_running_games(query, week):
    """
    This function is used to gather all games played up to the given week
    We can then use this subset of games to calculate the standings at
    the time of the game, which is used when displaying regular season results
    """
    subset = []
    for row in query:
        if row[WEEK] <= week:
            subset.append(row)
    return subset


def get_all_week_results(query):
    split_query = {}
    for row in query:
        if row[PLAYOFFS] == 0:
            week = row[WEEK]
            if week not in split_query:
                split_query[week] = [row]
            else:
                split_query[week].append(row)

    all_weeks = {}
    for week_number, results in split_query.items():
        subset = get_running_games(query, week_number)
        df = get_week_results(results, subset)
        df_html = df.to_html(classes="table-sm table-striped")
        all_weeks[week_number] = df_html

    return all_weeks


def get_playoff_results_for_season_summary(query):
    df = pd.DataFrame(columns=["Winning Team", "Losing Team", "Score"])

    playoffs_raw = get_playoffs(query)
    if not playoffs_raw:
        return None
    playoff_round_names = {}
    weeks = list(playoffs_raw.keys())
    if len(playoffs_raw) == 2:
        playoff_round_names[weeks[0]] = "Semifinals"
        playoff_round_names[weeks[1]] = "Championship"
    else:
        playoff_round_names[weeks[0]] = "Quarterfinals"
        playoff_round_names[weeks[1]] = "Semifinals"
        playoff_round_names[weeks[2]] = "Championship"

    all_playoff_weeks = {}
    for week, results in playoffs_raw.items():
        df = pd.DataFrame(columns=["Winning Team", "Losing Team", "Score"])
        for game in results:
            winning_team = f"#{game['winning_seed']} {game['winning_team']}"
            losing_team = f"#{game['losing_seed']} {game['losing_team']}"
            score = f"{game['winning_score']}-{game['losing_score']}"
            df.loc[len(df.index)] = [winning_team, losing_team, score]

        df.index += 1
        all_playoff_weeks[playoff_round_names[week]] = df.to_html(
            classes="table-sm table-striped")

    return all_playoff_weeks


def gen_points_df(query):
    league_members = get_league_members(query)
    points_df = pd.DataFrame(index=league_members)
    weeks = set()
    for row in query:
        if row[PLAYOFFS] == 0:
            week = row[WEEK]
            key = f"Week {week}"

            if key not in weeks:
                points_df[key] = 0.0
                weeks.add(key)

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_A_score = row[TEAM_A_SCORE]
            points_df.at[team_A_name, key] = team_A_score

            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
            team_B_score = row[TEAM_B_SCORE]
            points_df.at[team_B_name, key] = team_B_score
    return points_df


def get_roto(query):
    points_df = gen_points_df(query)
    standings, _ = get_standings(query)

    league_members = get_league_members(query)

    roto_df = pd.DataFrame(index=league_members,
                           columns=points_df.columns.to_list())
    for key in (points_df.columns.to_list()):
        points_temp = points_df.sort_values([key], ascending=True)
        for i in range(len(league_members)):
            member = points_temp.index.to_list()[i]
            roto_df[key][member] = i

    roto_df["Total"] = roto_df.iloc[:, :].sum(axis=1)
    standings, _ = get_standings(query)
    roto_df["PF"] = standings["PF"]

    roto_df = roto_df.sort_values(["Total", "PF"], ascending=False)
    roto_df["Total"] = roto_df["Total"].astype("int64")

    return roto_df


def get_projected_playoff_teams(standings: pd.DataFrame, ranks, roto: pd.DataFrame, num_total, num_roto):
    """

    Args:
        standings (pd.DataFrame): [h2h standings]
        ranks (Dict): [Rank of each member in the standings]
        roto (pd.DataFrame): [roto standings]
        num_total ([type]): [number of total teams in playoffs]
        num_roto ([type]): [number of roto teams into playoffs]

    Returns:
        A list of playoff teams merged betweet roto and h2h
    """

    playoff_teams = list(standings.index)[:num_total-num_roto]
    roto_index = list(roto.index)
    for member in roto_index:
        if member not in playoff_teams:
            playoff_teams.append(member)
            if len(playoff_teams) == num_total:
                break

    ret = []
    for member in playoff_teams:
        name = f"#{ranks[member]} {member}"
        if ranks[member] > num_total:
            name += "*"
        ret.append(name)
    return ret


def get_highest_score_from_week(scores):
    highest_score = 0
    member = ""
    for name, score in scores.items():
        if score > highest_score:
            highest_score = score
            member = name
    return member, highest_score


def get_week_winners(query, num_weeks):
    split_weeks = {}
    for row in query:
        week = row[WEEK]
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        if week not in split_weeks:
            split_weeks[week] = {
                team_A_name: row[TEAM_A_SCORE],
                team_B_name: row[TEAM_B_SCORE]
            }
        else:
            split_weeks[week][team_A_name] = row[TEAM_A_SCORE]
            split_weeks[week][team_B_name] = row[TEAM_B_SCORE]

    week_winners = []
    for week, value in split_weeks.items():
        week_winners.append(get_highest_score_from_week(value))
    while len(week_winners) < num_weeks:
        week_winners.append(("--", "--"))

    return week_winners


def get_overall_highest(query):
    high_score, member = 0, ""
    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_A_score = row[TEAM_A_SCORE]

        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        team_B_score = row[TEAM_B_SCORE]

        if team_A_score > high_score:
            high_score = team_A_score
            member = team_A_name

        if team_B_score > high_score:
            high_score = team_B_score
            member = team_B_name

    return member, high_score


def get_league_schedules(query):
    schedules_dict = {}
    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

        if team_A_name not in schedules_dict:
            schedules_dict[team_A_name] = [team_B_name]
        else:
            schedules_dict[team_A_name].append(team_B_name)

        if team_B_name not in schedules_dict:
            schedules_dict[team_B_name] = [team_A_name]
        else:
            schedules_dict[team_B_name].append(team_A_name)
    schedules_df = pd.DataFrame(schedules_dict)
    schedules_df["weeks"] = [f"Week {i + 1}" for i in range(len(schedules_df))]
    schedules_df = schedules_df.set_index(["weeks"])
    return schedules_df


def get_roto_against(query):
    roto_df = get_roto(query)
    schedules = get_league_schedules(query)

    # Drop the "Total" and "TPF" Columns
    columns = list(roto_df.columns)[:-2]
    rows = get_league_members(query)

    roto_against = pd.DataFrame(columns=columns, index=rows)

    for row in rows:
        for i in range(len(columns)):
            key = "Week " + str(i + 1)
            opponent = schedules.loc[key, row]
            roto_against.loc[row, key] = roto_df.loc[opponent, key]

    roto_against["Total"] = roto_against.iloc[:, :].sum(axis=1)
    roto_against["PA"] = get_standings(query)[0]["PA"]
    roto_against = roto_against.sort_values(
        ["Total", "PA"], ascending=False)
    roto_against = roto_against.convert_dtypes({"Total": "int64"})
    return roto_against


def get_head_to_head(query):
    points = gen_points_df(query)
    league_members = get_league_members(query)
    head2head = pd.DataFrame(columns=league_members, index=league_members)
    for a in league_members:
        for b in league_members:
            if a == b:
                head2head[b][a] = "--"
            else:
                wins = 0
                losses = 0
                for col in points.columns:
                    if points[col][a] > points[col][b]:
                        wins += 1
                    else:
                        losses += 1
                head2head[b][a] = str(wins) + "-" + str(losses)
    return head2head


def gen_wins_and_losses(query):
    wins_losses_dict = {}
    for row in query:
        team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
        team_A_score = row[TEAM_A_SCORE]

        team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
        team_B_score = row[TEAM_B_SCORE]

        team_A_result = "W" if team_A_score > team_B_score else "L"
        team_B_result = "W" if team_B_score > team_A_score else "L"

        if team_A_name not in wins_losses_dict:
            wins_losses_dict[team_A_name] = [team_A_result]
        else:
            wins_losses_dict[team_A_name].append(team_A_result)

        if team_B_name not in wins_losses_dict:
            wins_losses_dict[team_B_name] = [team_B_result]
        else:
            wins_losses_dict[team_B_name].append(team_B_result)

    wins_losses_df = pd.DataFrame(wins_losses_dict)
    wins_losses_df["Week"] = [
        f"Week {i + 1}" for i in range(len(wins_losses_df.index))]
    wins_losses_df = wins_losses_df.set_index(["Week"])
    return wins_losses_df


def update_interval(member, roto_points, result, intervals):
    column = "Top 3 Scorer"
    if roto_points <= 2:
        column = "Bottom 3 Scorer"
    elif roto_points <= 5:
        column = "Scored 7th-9th"
    elif roto_points <= 8:
        column = "Scored 4th-6th"

    record = intervals.loc[member, column]
    wins, losses = record.split("-")

    if result == "W":
        new_wins = str(int(wins) + 1)
        new_losses = losses
    else:
        new_wins = wins
        new_losses = str(int(losses) + 1)
    intervals.loc[member, column] = f"{new_wins}-{new_losses}"
    return intervals


def get_intervals(query):
    roto = get_roto(query)
    wins_and_losses = gen_wins_and_losses(query)

    columns = ["Top 3 Scorer", "Scored 4th-6th",
               "Scored 7th-9th", "Bottom 3 Scorer"]
    league_members = get_league_members(query)
    intervals = pd.DataFrame(columns=columns, index=league_members)
    intervals = intervals.fillna("0-0")
    for member in league_members:
        for week in roto.columns[:-2]:
            roto_points = roto.loc[member, week]
            result = wins_and_losses.loc[week, member]
            intervals = update_interval(member, roto_points, result, intervals)

    return intervals


def parse_rankings_filename(filename):
    # input resembles: power_rankings_week_n.json

    base_path = str(os.path.basename(filename))
    parts = base_path.split("_")
    n_json = parts[-1]
    week = n_json.split(".")[0]
    return week


def load_power_rankings(filename):
    data = json.load(open(filename, "r"))
    info = OrderedDict()
    for index, member in enumerate(data["rankings"]):
        info[member] = {
            "rank": index + 1,
            "change": 0
        }
    return info


def get_power_rankings_infos(filenames, week):
    for index, filename in enumerate(filenames):
        if week == parse_rankings_filename(filename):
            current_data = load_power_rankings(filename)
            if index == 0:
                previous_data = None
            else:
                previous_data = load_power_rankings(filenames[index - 1])

    return current_data, previous_data


def get_top_roto_scorers(tracker, roto_in: pd.DataFrame):
    columns = list(roto_in.columns)[:-2]
    for column in columns:
        winner = pd.to_numeric(roto_in[column]).idxmax()
        if winner not in tracker:
            tracker[winner] = 1
        else:
            tracker[winner] += 1
    return tracker


def get_top_three(input):
    if len(input) == 0:
        return []
    heapq.heapify(input)
    unique = OrderedDict()
    flag = True
    top_three = []

    while flag:
        x = heapq.heappop(input)
        if len(unique) == 3 and x.value not in unique:
            flag = False
            break
        else:
            top_three.append(x)
            if x.value not in unique:
                unique[x.value] = [x.name]
            else:
                unique[x.value].append(x.name)

    record_holders = []
    index = 1
    for key, value in unique.items():
        if len(value) == 1:
            record_holders.append(f"{index}. <b>{key}</b> - {value[0]}")
        else:
            for member in value:
                record_holders.append(f"T-{index}. <b>{key}</b> - {member}")
        index += 1

    return record_holders


def hall_of_fame_helper(query):
    most_points_all_time = []
    most_points_single_season_excl_playoffs = []
    most_ppg_all_time = []
    most_wins_overall = []
    most_wins_single_season_excl_playoffs = []
    most_wins_single_season_incl_playoffs = []
    most_playoff_wins = []
    longest_win_streak = []
    most_roto_points_all_time = []
    most_top_scoring_weeks = []

    league_members = get_league_members(query)
    for member in league_members:
        total_points, streak, _, _, _ = get_additional_stats(
            query, member)

        _, _, wins, _, po_wins, _ = get_overall_record(query, member)

        most_wins_overall.append(Record(member, wins))
        most_playoff_wins.append(Record(member, po_wins))
        most_points_all_time.append(Record(member, total_points))
        longest_win_streak.append(Record(member, streak))

    split_seasons_query = {}
    for row in query:
        year = row[SEASON]
        if year not in split_seasons_query:
            split_seasons_query[year] = [row]
        else:
            split_seasons_query[year].append(row)

    ppg_helper = {}
    all_time_roto_helper = {}
    roto_top_scorer_helper = {}
    champions = {2015: "Garrett Folbe",
                 2016: "Jonah Lopas"}

    for key, value in split_seasons_query.items():
        standings_playoffs, _ = get_standings(value, True)
        standings_reg, _ = get_standings(value)
        roto = get_roto(value)

        playoffs = get_playoffs(value)
        if playoffs:
            playoff_weeks = list(playoffs.keys())
            playoff_weeks.sort()
            champ_week = playoff_weeks[-1]
            if len(playoffs[champ_week]) == 1:
                champions[key] = playoffs[champ_week][0]["winning_team"]

        for index, row in standings_playoffs.iterrows():
            most_wins_single_season_incl_playoffs.append(
                Record(f"{index} ({key})", int(row["Wins"])))

            if index not in ppg_helper:
                ppg_helper[index] = {
                    "Total": row["PF"],
                    "Games": row["Wins"] + row["Losses"]
                }
            else:
                ppg_helper[index]["Total"] += row["PF"]
                ppg_helper[index]["Games"] += (row["Wins"] + row["Losses"])

        for index, row in standings_reg.iterrows():
            most_wins_single_season_excl_playoffs.append(
                Record(f"{index} ({key})", int(row["Wins"])))
            most_points_single_season_excl_playoffs.append(
                Record(f"{index} ({key})", round(row["PF"], 2))
            )

        for index, row in roto.iterrows():
            if index not in all_time_roto_helper:
                all_time_roto_helper[index] = row["Total"]
            else:
                all_time_roto_helper[index] += row["Total"]

        roto_top_scorer_helper = get_top_roto_scorers(
            roto_top_scorer_helper, roto)

    for key, value in all_time_roto_helper.items():
        most_roto_points_all_time.append(Record(f"{key}", int(value)))

    for key, value in ppg_helper.items():
        most_ppg_all_time.append(Record(f"{key}", round(
            value["Total"] / value["Games"], 2)))

    for key, value in roto_top_scorer_helper.items():
        most_top_scoring_weeks.append(Record(f"{key}", int(value)))

    top_3_most_points_all_time = get_top_three(most_points_all_time)

    top_3_most_points_single_season_excl_playoffs = get_top_three(
        most_points_single_season_excl_playoffs)

    top_3_most_ppg_all_time = get_top_three(most_ppg_all_time)

    top_3_most_wins_overall = get_top_three(most_wins_overall)

    top_3_most_wins_single_season_excl_playoffs = get_top_three(
        most_wins_single_season_excl_playoffs)

    top_3_most_wins_single_season_incl_playoffs = get_top_three(
        most_wins_single_season_incl_playoffs)

    top_3_most_playoff_wins = get_top_three(most_playoff_wins)

    top_3_longest_win_streak = get_top_three(longest_win_streak)

    top_3_most_roto_points_all_time = get_top_three(most_roto_points_all_time)

    top_3_most_top_scoring_weeks = get_top_three(most_top_scoring_weeks)

    return top_3_most_points_all_time, \
        top_3_most_points_single_season_excl_playoffs, \
        top_3_most_ppg_all_time, \
        top_3_most_wins_overall, \
        top_3_most_wins_single_season_excl_playoffs, \
        top_3_most_wins_single_season_incl_playoffs, \
        top_3_most_playoff_wins, \
        top_3_longest_win_streak, \
        top_3_most_roto_points_all_time, \
        top_3_most_top_scoring_weeks, \
        champions


def parse_jarrett_report_filename(file_name):
    # input resembles: jarrett_report_2021_week_17.json

    parts = file_name.split("_")
    year = int(parts[2])
    ending = parts[-1]
    week = int(ending.split(".")[0])

    return week, year
