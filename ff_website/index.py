import json
import pandas as pd
import inflect

from flask import flash, redirect, render_template, url_for, jsonify, request
from pandas.core.frame import DataFrame

from ff_website import app
from ff_website.apis import get_member_id
from ff_website.constants import *
from ff_website.db import get_db, init_db
from ff_website.forms import (CreateGame, CreateMember, GameQualities,
                              HeadToHead, SeasonSelector)

from ff_website.helper_functions import *


@app.route("/", methods=["GET", "POST"])
def hello():
    links = [
        {
            "title": "Current Season",
            "img_file": url_for("static", filename="img/current_season.png"),
            "description": "Find more information on this current season, including: standings, statistics, and more."
        },
        {
            "title": "Archives",
            "img_file": url_for("static", filename="img/archives.png"),
            "description": "Browse through members of previous seasons, pull up historical results, and compare league members head to head."
        },
        {
            "title": "Hall of Fame",
            "img_file": url_for("static", filename="img/hall_of_fame.png"),
            "description": "View the names of the enshrined members of our league who have etched their names in the history books."
        },
        {
            "title": "League Office",
            "img_file": url_for("static", filename="img/espn.png"),
            "description": "Visit our official home page on ESPN for your complete fantasy football experience."
        }
    ]

    return render_template("home.html", ql=links)


@app.route("/members", methods=["GET", "POST"])
def members():
    photo = "static/img/gmf.jpg"
    l = [photo for _ in range(12)]
    return render_template("league_members.html",  photos=l)


@app.route("/member/<int:id>", methods=["GET", "POST"])
def test(id):

    class Card:
        def __init__(self, text, value):
            self.text = text
            self.value = value

    cards = []

    db = get_db()

    member_info = db.execute(
        """
        SELECT * FROM member
        WHERE member_id=?
        """, (id,)
    ).fetchone()
    name = f"{member_info[FIRST_NAME]} {member_info[LAST_NAME]}"

    year_joined = member_info[YEAR_JOINED]

    all_games = db.execute(
        """
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.year_joined
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE team_A_id=? OR team_B_id=?
        """, (id, id)
    ).fetchall()

    last_year = all_games[-1][SEASON]
    record, po_record = get_overall_record(all_games, name)
    playoff_appearances = get_playoff_appearances(all_games)

    total_points, longest_win_streak, longest_losing_streak, most_points, fewest_points = get_additional_stats(
        all_games, name)

    total_points_str = "{:.2f}".format(total_points)
    avg_points_str = "{:.2f}".format(total_points/len(all_games))

    cards.append(Card("Total Games", len(all_games)))
    cards.append(Card("Overall Record", record))
    cards.append(Card("Playoff Record", po_record))
    cards.append(Card("Total Points", total_points_str))
    cards.append(Card("Points per game", avg_points_str))
    cards.append(Card("Most Points", most_points))
    cards.append(Card("Fewest Points", fewest_points))
    cards.append(Card("Longest Win Streak", longest_win_streak))
    cards.append(Card("Longest Losing Streak", longest_losing_streak))

    seasons = get_schedules(all_games, name)

    return render_template("member.html",
                           name=name,
                           year_joined=year_joined,
                           last_year=last_year,
                           playoff_appearances=playoff_appearances,
                           cards=cards,
                           seasons=seasons)


@ app.route("/archives/", methods=["GET", "POST"])
def archives_home():
    return render_template("archives_home.html")


@ app.route("/archives/head_to_head", methods=["GET", "POST"])
def h2h():

    # Initialize variables that will be returned on successful submission of the form
    # If we do not make the variables None-types, the template cannot be rendered
    team_A_name, team_B_name, series_winner_name, num_matchups, num_times, series_split, tied, num_playoff_matchups, num_regular_matchups, streak_count, streak_holder = None, None, None, None, None, None, None, None, None, None, None

    args = request.args
    form = HeadToHead()
    total_points = 0
    margin_of_victory = 0
    df = pd.DataFrame(columns=[
        "Season", "Week", "Matchup Format", "Winning Team", "Losing Team", "Score"])

    # Get the member_ids from the request
    member_one_id, member_two_id = None, None
    try:
        member_one_id = args.get("member_one_id")
        member_two_id = args.get("member_two_id")
    except AttributeError as e:
        print("Something went wrong getting parameters!", e)

    # If we got the members successfully, find the history of their games
    if member_one_id and member_two_id:
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "Winning Team", "Losing Team", "Score"])

        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE team_A_id = ? AND team_B_id = ? OR team_A_id = ? AND team_B_id = ?
            """, (member_one_id, member_two_id,
                  member_two_id, member_one_id)
        ).fetchall()
        for row in query:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]
            total_points += (float(team_A_score) + float(team_B_score))

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]
            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            winning_team = team_A_name if team_A_score > team_B_score else team_B_name
            losing_team = team_A_name if team_A_score < team_B_score else team_B_name

            winning_score = team_A_score if team_A_score > team_B_score else team_B_score
            losing_score = team_A_score if team_A_score < team_B_score else team_B_score
            margin_of_victory += (float(winning_score) - float(losing_score))

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, winning_team, losing_team, f"{winning_score}-{losing_score}{asterisk}"]

        num_matchups = len(df.index)
        if num_matchups > 0:
            try:
                margin_of_victory /= num_matchups
            except:
                ZeroDivisionError

            series_winner_name, series_split, tied = get_series_split(df)
            num_regular_matchups, num_playoff_matchups = get_matchup_breakdown(
                df)
            streak_holder, streak_count = get_streak_head_to_head(df)
            df.index += 1
            p = inflect.engine()
            num_times = p.plural("time", num_matchups)
        else:
            # We still need to get the names of the members. We sort the member_ids by ascending
            # order to keep track of which name gets returned first
            query = db.execute(
                f"""
                SELECT {MEMBER_ID}, {FIRST_NAME}, {LAST_NAME} from member
                WHERE {MEMBER_ID}=? OR {MEMBER_ID}=?
                ORDER BY {MEMBER_ID} asc
                """, (member_one_id, member_two_id)
            ).fetchall()
            if len(query) == 2:
                if member_one_id < member_two_id:
                    team_A_name = f"{query[0]['first_name']} {query[0]['last_name']}"
                    team_B_name = f"{query[1]['first_name']} {query[1]['last_name']}"
                else:
                    team_A_name = f"{query[0]['first_name']} {query[1]['last_name']}"
                    team_B_name = f"{query[1]['first_name']} {query[0]['last_name']}"
        db.close()
    if form.validate_on_submit():
        return redirect(url_for("h2h", member_one_id=form.data["leagueMemberOne"], member_two_id=form.data["leagueMemberTwo"]))

    return render_template("head_to_head.html",
                           form=form,
                           team_A_name=team_A_name,
                           team_B_name=team_B_name,
                           num_matchups=num_matchups,
                           num_times=num_times,
                           series_winner_name=series_winner_name,
                           tied=tied,
                           series_split=series_split,
                           num_playoff_matchups=num_playoff_matchups,
                           num_regular_matchups=num_regular_matchups,
                           total_points=round(total_points, 2),
                           margin_of_victory=round(margin_of_victory, 2),
                           streak_holder=streak_holder,
                           streak_count=streak_count,
                           df=df.to_html(classes="table table-striped"),
                           matchups_exist=num_matchups != 0
                           )


@ app.route("/archives/game_qualities", methods=["GET", "POST"])
def game_qualities():
    form = GameQualities()
    args = request.args

    df = pd.DataFrame(columns=[
        "Season", "Week", "Matchup Format", "Winning Team", "Losing Team", "Score"])
    try:
        filter_type = args.get("filter_type")
        num_results = args.get("num_results")
    except AttributeError as e:
        print("Something went wrong getting paramters", e)

    # Fewest points scored combined
    if filter_type == "1":
        total_scores_list = []
        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs, team_A_score+team_B_score as total_score,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            ORDER BY total_score ASC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            winning_team = team_A_name if team_A_score > team_B_score else team_B_name
            losing_team = team_A_name if team_A_score < team_B_score else team_B_name

            winning_score = team_A_score if team_A_score > team_B_score else team_B_score
            losing_score = team_A_score if team_A_score < team_B_score else team_B_score

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, winning_team, losing_team, f"{winning_score}-{losing_score}{asterisk}"]

            total_scores_list.append(row["total_score"])
        df["Total Points"] = total_scores_list
        db.close()

    # Fewest points scored individual
    if filter_type == "2":
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "League Member", "Points"])
        db = get_db()
        query = db.execute(
            f"""
            WITH t as(
                SELECT game_id, team_A_score as points, season, week, matchup_length, playoffs, team_A_id as team_id from game
                UNION ALL
                SELECT game_id, team_B_score as points, season, week, matchup_length, playoffs, team_B_id as team_id from game
                ORDER BY team_A_score DESC
            )
            SELECT points, season, week, matchup_length, playoffs, team_id, first_name, last_name
            FROM t
            INNER JOIN member on member_id = team_id
            ORDER BY points ASC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            points = row["points"]
            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_name = f"{row['first_name']} {row['last_name']}"

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, team_name, points]
        db.close()

    # Most points scored combined
    if filter_type == "3":
        total_scores_list = []
        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs, team_A_score+team_B_score as total_score,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            ORDER BY total_score DESC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            winning_team = team_A_name if team_A_score > team_B_score else team_B_name
            losing_team = team_A_name if team_A_score < team_B_score else team_B_name

            winning_score = team_A_score if team_A_score > team_B_score else team_B_score
            losing_score = team_A_score if team_A_score < team_B_score else team_B_score

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, winning_team, losing_team, f"{winning_score}-{losing_score}{asterisk}"]

            total_scores_list.append(row["total_score"])
        df["Total Points"] = total_scores_list
        db.close()

    # Fewest points scored combined
    if filter_type == "4":
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "League Member", "Points"])
        db = get_db()
        query = db.execute(
            f"""
            WITH t as(
                SELECT game_id, team_A_score as points, season, week, matchup_length, playoffs, team_A_id as team_id from game
                UNION ALL
                SELECT game_id, team_B_score as points, season, week, matchup_length, playoffs, team_B_id as team_id from game
                ORDER BY team_A_score DESC
            )
            SELECT points, season, week, matchup_length, playoffs, team_id, first_name, last_name
            FROM t
            INNER JOIN member on member_id = team_id
            ORDER BY points DESC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            points = row["points"]
            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_name = f"{row['first_name']} {row['last_name']}"

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, team_name, points]
        db.close()

    # Largest margin of victory
    if filter_type == "5":
        deficits_list = []
        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs, abs(team_A_score-team_B_score) as margin,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            ORDER BY margin DESC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            winning_team = team_A_name if team_A_score > team_B_score else team_B_name
            losing_team = team_A_name if team_A_score < team_B_score else team_B_name

            winning_score = team_A_score if team_A_score > team_B_score else team_B_score
            losing_score = team_A_score if team_A_score < team_B_score else team_B_score

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, winning_team, losing_team, f"{winning_score}-{losing_score}{asterisk}"]

            deficits_list.append(row["margin"])
        df["Margin"] = deficits_list
        db.close()

    # Smallest margin of victory
    if filter_type == "6":
        deficits_list = []
        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs, abs(team_A_score-team_B_score) as margin,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            ORDER BY margin ASC LIMIT {num_results}
            """
        ).fetchall()
        for row in query:
            team_A_score = row["team_A_score"]
            team_B_score = row["team_B_score"]

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            team_A_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
            team_B_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

            winning_team = team_A_name if team_A_score > team_B_score else team_B_name
            losing_team = team_A_name if team_A_score < team_B_score else team_B_name

            winning_score = team_A_score if team_A_score > team_B_score else team_B_score
            losing_score = team_A_score if team_A_score < team_B_score else team_B_score

            asterisk = "*" if matchup_length == 2 else ""
            matchup_format = "Playoffs" if playoffs else "Regular Season"
            df.loc[len(df.index)] = [season, week,
                                     matchup_format, winning_team, losing_team, f"{winning_score}-{losing_score}{asterisk}"]

            deficits_list.append(row["margin"])
        df["Margin"] = deficits_list
        db.close()

    df.index += 1

    if form.validate_on_submit():
        return redirect(url_for("game_qualities", filter_type=form.data["filter"], num_results=form.data["numberOfResults"]))

    return render_template("game_qualities.html",
                           form=form,
                           query_specified=len(df.index != 0),
                           df=df.to_html(classes="table table-striped"))


@ app.route("/archives/season_summary", methods=["GET", "POST"])
def season_summary():

    form = SeasonSelector()
    args = request.args
    year, standings = None, None

    standings = pd.DataFrame()

    try:
        year = args.get("year")
    except AttributeError as e:
        print("Something went wrong getting parameters", e)

    if year:
        db = get_db()
        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE season=?
            """, (year,)
        ).fetchall()

        standings, ranks = get_standings(query)
        x = get_playoffs(query, ranks)

    if form.validate_on_submit():
        return redirect(url_for("season_summary", year=form.data["year"]))

    return render_template("season_summary.html",
                           form=form,
                           year=year,
                           standings=standings.to_html(classes="table table-striped"))


@ app.route("/tools/create_member", methods=["GET", "POST"])
def create_member():
    form = CreateMember()
    if form.validate_on_submit():
        db = get_db()
        query = db.execute(
            f"""
            SELECT {MEMBER_ID}, {LAST_NAME} FROM member
            WHERE {FIRST_NAME}=? AND {LAST_NAME}=?
            """,
            (form.data["firstName"], form.data["lastName"])
        ).fetchone()
        if query:
            form.firstName.errors.append(
                "A member of this name already exists")
            form.lastName.errors.append(
                "A member of this name already exists")
        else:
            db.execute(
                f"""
                INSERT INTO member
                ({FIRST_NAME}, {LAST_NAME}, {YEAR_JOINED}, {ACTIVE})
                VALUES(?, ?, ?, ?)
                """, (form.data["firstName"], form.data["lastName"],
                      form.data["initialYear"], form.data["activeMember"])
            )
            db.commit()
            db.close()
            flash('Member created!', 'success')
            return redirect(url_for('create_member'))

    return render_template("create_member.html", form=form)


@ app.route("/tools/create_game", methods=["GET", "POST"])
def create_game():
    form = CreateGame()
    if form.validate_on_submit():
        db = get_db()
        query = db.execute(
            f"""
            SELECT {TEAM_A_ID}, {TEAM_B_ID}, {WEEK}, {SEASON} FROM game
            WHERE {TEAM_A_ID}=? AND {TEAM_B_ID}=? AND {WEEK}=? AND {SEASON}=?
            """,
            (form.data["teamAName"], form.data["teamBName"],
             form.data["week"], form.data["season"])
        ).fetchone()
        if query:
            form.teamAName.errors.append(
                "A game with these two opponents already exists at the given date"
            )
            form.teamBName.errors.append(
                "A game with these two opponents already exists at the given date"
            )
            form.week.errors.append(
                "A game with these two opponents already exists at the given date"
            )
            form.season.errors.append(
                "A game with these two opponents already exists at the given date"
            )
        else:
            db.execute(
                f"""
                INSERT INTO game
                ({TEAM_A_SCORE}, {TEAM_B_SCORE}, {SEASON}, {WEEK},
                {MATCHUP_LENGTH}, {PLAYOFFS}, {TEAM_A_ID}, {TEAM_B_ID})
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (form.data["teamAScore"], form.data["teamBScore"], form.data["season"],
                 form.data["week"], form.data["matchupLength"], form.data["playoffs"],
                 form.data["teamAName"], form.data["teamBName"])
            )
            db.commit()
            db.close()
            flash('Game created!', 'success')
            return redirect(url_for('create_game'))

    return render_template("create_game.html", form=form)


@ app.route("/apis/add_all_members", methods=["GET", "POST"])
def add_league_members():

    db = get_db()

    # Clear table
    db.execute(
        """
        DELETE FROM member
        """
    )

    members = json.load(open(member_data, "r"))

    for member in members:
        db.execute(
            """
            INSERT INTO member(
                first_name, last_name, year_joined, active)
                VALUES (?, ?, ?, ?)
            """,
            (member[FIRST_NAME], member[LAST_NAME],
             member[YEAR_JOINED], member[ACTIVE])
        )
    db.commit()

    return jsonify(members)


@ app.route("/apis/add_all_games", methods=["GET", "POST"])
def add_games():
    db = get_db()

    # Clear table
    db.execute(
        """
        DELETE FROM game
        """
    )
    db.commit()
    games = json.load(open(games_data, "r"))

    for game in games:
        first_name_home, last_name_home = game[HOME_TEAM].split(" ")
        member_id_home = get_member_id(first_name_home, last_name_home)

        first_name_away, last_name_away = game[AWAY_TEAM].split(" ")
        member_id_away = get_member_id(first_name_away, last_name_away)

        db = get_db()
        db.execute(
            f"""
            INSERT INTO game(
                {TEAM_A_SCORE}, {TEAM_B_SCORE}, {SEASON}, {WEEK},
                {MATCHUP_LENGTH}, {PLAYOFFS}, {TEAM_A_ID}, {TEAM_B_ID}
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (game[HOME_SCORE], game[AWAY_SCORE],
             game[SEASON], game[WEEK], game[MATCHUP_LENGTH],
             game[PLAYOFFS], member_id_home, member_id_away)
        )
        db.commit()

    return jsonify(games)
