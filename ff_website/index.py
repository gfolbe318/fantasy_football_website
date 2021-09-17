import glob
import json
import os
from pathlib import Path
from collections import OrderedDict

import inflect
import pandas as pd
from flask import flash, jsonify, redirect, render_template, request, url_for
from PIL import Image

from ff_website import app
from ff_website.apis import get_member_id
from ff_website.constants import *
from ff_website.db import get_db
from ff_website.forms import (CreateGame, CreateMember, CreatePowerRankings,
                              GameQualities, HeadToHead, SeasonSelector, selectPowerRankWeek)
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
            "description": "Browse through members of previous seasons, pull up historical results, and compare league members head to head.",
            "link": url_for("archives_home")
        },
        {
            "title": "Hall of Fame",
            "img_file": url_for("static", filename="img/hall_of_fame.png"),
            "description": "View the names of the enshrined members of our league who have etched their names in the history books."
        },
        {
            "title": "League Office",
            "img_file": url_for("static", filename="img/espn.png"),
            "description": "Visit our official home page on ESPN for your complete fantasy football experience.",
            "link": "https://fantasy.espn.com/football/league?leagueId=50890012"
        }
    ]

    return render_template("home.html", ql=links)


@app.route("/members", methods=["GET", "POST"])
def members():
    db = get_db()
    data = db.execute(
        f"""
        SELECT * FROM member
        WHERE {ACTIVE}=?
        """, (1,)
    ).fetchall()
    cards = []
    for member in data:
        cards.append({
            MEMBER_ID: member[MEMBER_ID],
            "name": f"{member[FIRST_NAME]} {member[LAST_NAME]}",
            IMG_FILEPATH: url_for(
                'static', filename=f"img/avatars/{member[IMG_FILEPATH]}")
        })

    return render_template("league_members.html", title="Current Members", cards=cards)


@app.route("/archives/inactive_members", methods=["GET", "POST"])
def inactive_members():
    db = get_db()
    data = db.execute(
        f"""
        SELECT * FROM member
        WHERE {ACTIVE}=?
        """, (0,)
    ).fetchall()
    cards = []
    for member in data:
        cards.append({
            MEMBER_ID: member[MEMBER_ID],
            "name": f"{member[FIRST_NAME]} {member[LAST_NAME]}",
            IMG_FILEPATH: url_for(
                'static', filename=f"img/avatars/{member[IMG_FILEPATH]}")
        })

    return render_template("league_members.html", title="Inactive Members", cards=cards)


@app.route("/tools", methods=["GET", "POST"])
def tools():
    return render_template("tools.html")


@app.route("/tools/list_all_members", methods=["GET", "POST"])
def list_members():
    db = get_db()
    all_members = db.execute(
        """
        SELECT * FROM member
        """
    ).fetchall()
    db.close()
    data = [
        {
            MEMBER_ID: i[MEMBER_ID],
            FIRST_NAME: i[FIRST_NAME],
            LAST_NAME: i[LAST_NAME],
            YEAR_JOINED: i[YEAR_JOINED],
            ACTIVE: i[ACTIVE],
            IMG_FILEPATH: i[IMG_FILEPATH]

        } for i in all_members
    ]
    return render_template("members_admin.html", data=data)


@app.route("/tools/update_member/<int:member_id>", methods=["GET", "POST"])
def update_member(member_id):
    db = get_db()
    info = db.execute(
        """
        SELECT * from member WHERE
        member_id=?
        """, (member_id,)
    ).fetchone()

    first_name = info[FIRST_NAME]
    last_name = info[LAST_NAME]
    year_joined = info[YEAR_JOINED]
    status = info[ACTIVE]
    form = CreateMember(firstName=first_name,
                        lastName=last_name,
                        initialYear=str(year_joined),
                        activeMember=str(status))

    if form.validate_on_submit():
        if form.firstName.data == first_name and form.lastName.data == last_name and form.initialYear.data == str(year_joined) and form.activeMember.data == str(status) and form.image.data == None:
            flash('Member not changed.', 'warning')
            return redirect(url_for('list_members'))
        else:
            new_first_name = form.firstName.data
            new_last_name = form.lastName.data
            new_year_joined = int(form.initialYear.data)
            new_status = int(form.activeMember.data)

            photo = form.data["image"]
            file_name = "default.png"
            if photo:
                first_name = form.data["firstName"]
                last_name = form.data["lastName"]
                extension = os.path.splitext(photo.filename)[1]
                file_name = f"{first_name}_{last_name}{extension}"
                full_file_path = os.path.join(
                    app.root_path, Path('static/img/avatars/', file_name)
                )
                output_size = (800, 800)
                i = Image.open(photo)
                i = i.resize(output_size)
                i.save(full_file_path)

            db.execute(
                f"""
                UPDATE member
                SET {FIRST_NAME}=?, {LAST_NAME}=?, {YEAR_JOINED}=?, {ACTIVE}=?, {IMG_FILEPATH}=?
                WHERE {MEMBER_ID}=?
                """, (new_first_name, new_last_name, new_year_joined, new_status, file_name, member_id)
            )
            db.commit()
            db.close()
            flash('Member updated!', 'success')
            return redirect(url_for('tools'))

    return render_template("update_member.html",
                           form=form,
                           first_name=first_name,
                           last_name=last_name,
                           year_joined=year_joined,
                           status=status)


@app.route("/tools/delete_member/<int:member_id>", methods=["GET", "POST"])
def delete_member(member_id):
    db = get_db()
    query = db.execute(
        f"""
        SELECT {FIRST_NAME}, {LAST_NAME}
        FROM member
        WHERE {MEMBER_ID}=?
        """, (member_id,)
    ).fetchall()
    first_name = query[0][FIRST_NAME]
    last_name = query[0][LAST_NAME]

    # This is the ugliest code I've ever written. If everyone ever reads it, I apologize.
    jpg_path_uc = os.path.join(app.root_path, "static", "img", "avatars",
                               f"{first_name}_{last_name}.JPG")
    jpg_path_lc = os.path.join(app.root_path, "static", "img", "avatars",
                               f"{first_name}_{last_name}.jpg")

    png_path_uc = os.path.join(app.root_path, "static", "img", "avatars",
                               f"{first_name}_{last_name}.PNG")

    png_path_lc = os.path.join(app.root_path, "static", "img", "avatars",
                               f"{first_name}_{last_name}.png")

    try:
        os.remove(jpg_path_lc)
    except OSError:
        print("Error while deleting file")
    try:
        os.remove(jpg_path_uc)
    except OSError:
        print("Error while deleting file")
    try:
        os.remove(png_path_lc)
    except OSError:
        print("Error while deleting file")
    try:
        os.remove(png_path_uc)
    except OSError:
        print("Error while deleting file")

    db.execute(
        """
        DELETE FROM member
        WHERE member_id=?
        """, (member_id,)
    )
    db.commit()
    db.close()
    flash('Member deleted!', 'danger')
    return redirect(url_for('tools'))


@app.route("/tools/list_all_games", methods=["GET", "POST"])
def list_games():
    db = get_db()
    all_games = db.execute(
        """
        SELECT * FROM game
        """
    ).fetchall()
    df = pd.DataFrame(columns=["id", "Season", "Week", "Playoffs",
                               "Team_A_id", "Team_A_score", "Team_B_id", "Team_B_score", "Edit", "Delete"])

    for index, element in enumerate(all_games):
        df.loc[index] = [
            element[GAME_ID],
            element[SEASON],
            element[WEEK],
            element[PLAYOFFS],
            element[TEAM_A_ID],
            element[TEAM_A_SCORE],
            element[TEAM_B_ID],
            element[TEAM_B_SCORE],
            "Placeholder",
            "Placeholder"
        ]

    return render_template("games_admin.html", df=df)


@app.route("/tools/update_game/<int:game_id>", methods=["GET", "POST"])
def update_game(game_id):
    db = get_db()
    info = db.execute(
        """
        SELECT * from game WHERE
        game_id=?
        """, (game_id,)
    ).fetchone()
    season = info[SEASON]
    week = info[WEEK]
    team_A_id = info[TEAM_A_ID]
    team_A_score = info[TEAM_A_SCORE]
    team_B_id = info[TEAM_B_ID]
    team_B_score = info[TEAM_B_SCORE]
    playoffs = info[PLAYOFFS]
    matchup_length = info[MATCHUP_LENGTH]
    form = CreateGame(season=season,
                      week=week,
                      teamAName=team_A_id,
                      teamAScore=team_A_score,
                      teamBName=team_B_id,
                      teamBScore=team_B_score,
                      playoffs=playoffs,
                      matchupLength=matchup_length)

    if form.validate_on_submit():
        if form.season.data == str(season) and \
                form.week.data == str(week) and \
                form.teamAName.data == str(team_A_id) and \
                form.teamAScore.data == team_A_score and \
                form.teamBName.data == str(team_B_id) and \
                form.teamBScore.data == team_B_score and \
                form.playoffs.data == str(playoffs) and \
                form.matchupLength.data == str(matchup_length):
            flash('Game not changed.', 'warning')
            return redirect(url_for('tools'))
        else:
            new_week = form.week.data
            new_season = form.season.data
            new_team_A_name = form.teamAName.data
            new_team_A_score = form.teamAScore.data
            new_team_B_name = form.teamBName.data
            new_team_B_score = form.teamBScore.data
            new_playoffs = form.playoffs.data
            new_matchup_length = form.matchupLength.data

            db.execute(
                f"""
                UPDATE game
                SET {WEEK}=?, {SEASON}=?, {TEAM_A_ID}=?, {TEAM_A_SCORE}=?, {TEAM_B_ID}=?, {TEAM_B_SCORE}=?, {PLAYOFFS}=?, {MATCHUP_LENGTH}=?
                WHERE {GAME_ID}=?
                """, (new_week, new_season, new_team_A_name, new_team_A_score, new_team_B_name, new_team_B_score, new_playoffs, new_matchup_length, game_id)
            )
            db.commit()
            db.close()
            flash('Game updated!', 'success')
            return redirect(url_for('tools'))

    return render_template("update_game.html", form=form)


@app.route("/tools/delete_game/<int:game_id>", methods=["GET", "POST"])
def delete_game(game_id):
    db = get_db()
    db.execute(
        """
        DELETE FROM game
        WHERE game_id=?
        """, (game_id,)
    )
    db.commit()
    db.close()
    flash('Game deleted!', 'danger')
    return redirect(url_for('tools'))


@app.route("/member/<int:member_id>", methods=["GET", "POST"])
def get_member_info(member_id):

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
        """, (member_id,)
    ).fetchone()
    name = f"{member_info[FIRST_NAME]} {member_info[LAST_NAME]}"
    img_filepath = member_info[IMG_FILEPATH]

    year_joined = member_info[YEAR_JOINED]

    all_games_for_member = db.execute(
        """
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.year_joined
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE team_A_id=? OR team_B_id=?
        """, (member_id, member_id)
    ).fetchall()

    all_games = db.execute(
        """
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.year_joined
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
        """
    ).fetchall()

    last_year = all_games_for_member[-1][SEASON]
    record, po_record = get_overall_record(all_games_for_member, name)
    playoff_appearances = get_playoff_appearances(all_games_for_member)

    total_points, longest_win_streak, longest_losing_streak, most_points, fewest_points = get_additional_stats(
        all_games_for_member, name)

    total_points_str = "{:.2f}".format(total_points)
    avg_points_str = "{:.2f}".format(total_points/len(all_games_for_member))

    cards.append(Card("Total Games", len(all_games_for_member)))
    cards.append(Card("Overall Record", record))
    cards.append(Card("Playoff Record", po_record))
    cards.append(Card("Total Points", total_points_str))
    cards.append(Card("Points per game", avg_points_str))
    cards.append(Card("Most Points", most_points))
    cards.append(Card("Fewest Points", fewest_points))
    cards.append(Card("Longest Win Streak", longest_win_streak))
    cards.append(Card("Longest Losing Streak", longest_losing_streak))

    summaries = get_summaries(all_games, name)
    championships = get_championships(summaries, name)
    summaries_html = summaries.to_html(classes="table table-striped")
    seasons = get_schedules(all_games_for_member, name)

    return render_template("member.html",
                           name=name,
                           img_filepath=img_filepath,
                           year_joined=year_joined,
                           last_year=last_year,
                           playoff_appearances=playoff_appearances,
                           championships=championships,
                           cards=cards,
                           summaries=summaries_html,
                           seasons=seasons)


@ app.route("/archives/", methods=["GET", "POST"])
def archives_home():
    return render_template("archives_home.html")


@ app.route("/archives/head_to_head", methods=["GET", "POST"])
def h2h():

    # Initialize variables that will be returned on successful submission of the form
    # If we do not make the variables None-types, the template cannot be rendered
    team_A_name, team_B_name, team_A_img, team_B_img, series_winner_name, num_matchups, num_times, series_split, tied, num_playoff_matchups, num_regular_matchups, streak_count, streak_holder = None, None, None, None, None, None, None, None, None, None, None, None, None

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
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t2.img_filepath as team_A_img_filepath,
            t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.img_filepath as team_B_img_filepath
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
            team_A_img = row["team_A_img_filepath"]
            team_B_img = row["team_B_img_filepath"]

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
                SELECT {MEMBER_ID}, {FIRST_NAME}, {LAST_NAME}, {IMG_FILEPATH} from member
                WHERE {MEMBER_ID}=? OR {MEMBER_ID}=?
                ORDER BY {MEMBER_ID} asc,
                """, (member_one_id, member_two_id)
            ).fetchall()
            if len(query) == 2:
                if member_one_id < member_two_id:
                    team_A_name = f"{query[0]['first_name']} {query[0]['last_name']}"
                    team_B_name = f"{query[1]['first_name']} {query[1]['last_name']}"
                    team_A_img = query[0]["team_A_img_filepath"]
                    team_B_img = query[1]["team_B_img_filepath"]
                else:
                    team_A_name = f"{query[1]['first_name']} {query[1]['last_name']}"
                    team_B_name = f"{query[0]['first_name']} {query[0]['last_name']}"
                    team_A_img = query[1]["team_A_img_filepath"]
                    team_B_img = query[0]["team_B_img_filepath"]
        db.close()
    if form.validate_on_submit():
        return redirect(url_for("h2h", member_one_id=form.data["leagueMemberOne"], member_two_id=form.data["leagueMemberTwo"]))

    return render_template("head_to_head.html",
                           form=form,
                           team_A_name=team_A_name,
                           team_B_name=team_B_name,
                           team_A_img=team_A_img,
                           team_B_img=team_B_img,
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
    year, standings, all_weeks, roto, playoffs = None, None, None, None, None

    standings = pd.DataFrame()
    roto = pd.DataFrame()

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

        standings, _ = get_standings(query)
        playoffs = get_playoff_results_for_season_summary(query)
        all_weeks = get_all_week_results(query)
        roto = get_roto(query)

    if form.validate_on_submit():
        return redirect(url_for("season_summary", year=form.data["year"]))

    return render_template("season_summary.html",
                           form=form,
                           year=year,
                           all_weeks=all_weeks,
                           roto=roto.to_html(classes="table table-striped"),
                           playoffs=playoffs,
                           standings=standings.to_html(classes="table table-striped"))


@ app.route("/tools/create_member", methods=["GET", "POST"])
def create_member():
    form = CreateMember()
    if form.validate_on_submit():
        db = get_db()
        query = db.execute(
            f"""
            SELECT {MEMBER_ID} FROM member
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
            photo = form.data["image"]
            first_name = form.data["firstName"]
            last_name = form.data["lastName"]
            file_name = "default.png"
            if photo:
                extension = os.path.splitext(photo.filename)[1]
                file_name = f"{first_name}_{last_name}{extension}"
                full_file_path = os.path.join(
                    app.root_path, Path('static/img/avatars/', file_name)
                )
                output_size = (800, 800)
                i = Image.open(photo)
                i = i.resize(output_size)
                i.save(full_file_path)

            db.execute(
                f"""
                INSERT INTO member
                ({FIRST_NAME}, {LAST_NAME}, {YEAR_JOINED}, {ACTIVE}, {IMG_FILEPATH})
                VALUES(?, ?, ?, ?, ?)
                """, (first_name, last_name, form.data["initialYear"], form.data["activeMember"], file_name)
            )
            db.commit()
            db.close()
            flash('Member created!', 'success')
            return redirect(url_for('tools'))

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


@ app.route("/tools/add_all_members", methods=["GET", "POST"])
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
                first_name, last_name, year_joined, active, img_filepath)
                VALUES (?, ?, ?, ?, ?)
            """,
            (member[FIRST_NAME], member[LAST_NAME],
             member[YEAR_JOINED], member[ACTIVE], member[IMG_FILEPATH])
        )
    db.commit()

    return jsonify(members)


@ app.route("/tools/add_all_games", methods=["GET", "POST"])
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


@app.route("/tools/create_power_rankings", methods=["GET", "POST"])
def create_power_rankings():
    db = get_db()
    actives_query = db.execute(
        f"""
        SELECT {MEMBER_ID} FROM member
        WHERE {ACTIVE}=?
        """, (1,)
    ).fetchall()

    form = CreatePowerRankings(year=CURRENT_SEASON)
    if form.validate_on_submit():
        team_one = form.team_one.data
        team_two = form.team_two.data
        team_three = form.team_three.data
        team_four = form.team_four.data
        team_five = form.team_five.data
        team_six = form.team_six.data
        team_seven = form.team_seven.data
        team_eight = form.team_eight.data
        team_nine = form.team_nine.data
        team_ten = form.team_ten.data
        team_eleven = form.team_eleven.data
        team_twelve = form.team_twelve.data
        submitted = [team_one, team_two, team_three, team_four, team_five, team_six,
                     team_seven, team_eight, team_nine, team_ten, team_eleven, team_twelve]

        submitted_set = set(submitted)
        actives_set = set([str(row[MEMBER_ID]) for row in actives_query])

        missing = actives_set - submitted_set
        if len(missing) == 0:
            year = form.year.data
            week = form.week.data
            file_name = f"power_rankings_week_{week}.json"

            query = db.execute(
                f"""
                SELECT {MEMBER_ID}, {FIRST_NAME}, {LAST_NAME}
                FROM member
                """
            ).fetchall()
            names_dict = {}
            for row in query:
                name = row[FIRST_NAME] + " " + row[LAST_NAME]
                names_dict[row[MEMBER_ID]] = name

            object = {
                "year": year,
                "week": week,
                "rankings": [names_dict[int(i)] for i in submitted]
            }

            file_path = os.path.join(
                app.root_path, "data", "power_rankings", year)
            os.makedirs(file_path, exist_ok=True)
            json.dump(object, open(os.path.join(file_path, file_name), "w"))
            db.close()
            flash('Power Rankings Created!', 'success')
            return redirect(url_for('tools'))

        else:
            # This fixes the bug where a single member was missed from power rankings
            if len(missing) == 1:
                elem = list(missing)[0]
                query = db.execute(
                    f"""
                    SELECT {FIRST_NAME}, {LAST_NAME} FROM member
                    WHERE {MEMBER_ID}=?
                    """, (elem,)
                ).fetchall()
            else:
                query = db.execute(
                    f"""
                    SELECT {FIRST_NAME}, {LAST_NAME} FROM member
                    WHERE {MEMBER_ID} IN {tuple(missing)}
                    """
                ).fetchall()
            names = [name[FIRST_NAME] + " " + name[LAST_NAME]
                     for name in query]
            names_str = ""
            for i, name in enumerate(names):
                names_str += name
                if i != len(names):
                    names_str += ", "
            form.submit.errors.append(
                "The following members aren't present: " + names_str)
            flash('Power Rankings Failed to Create!', 'danger')

    db.close()
    return render_template("create_power_rankings.html", form=form)


@app.route("/current_season", methods=["GET", "POST"])
def current_season():
    return render_template("current_season.html", cards=CURRENT_SEASON_CARDS)


@app.route("/current_season/standings", methods=["GET", "POST"])
def current_season_standings():
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
            """, (CURRENT_SEASON,)
    ).fetchall()

    standings, ranks = get_standings(query)
    standings_html = standings.to_html(classes="table table-striped")

    roto = get_roto(query)
    roto_html = roto.to_html(classes="table table-striped")

    matchups = get_projected_playoff_teams(
        standings, ranks, roto, 6, 1)

    return render_template("current_season_standings.html",
                           cards=CURRENT_SEASON_CARDS,
                           standings=standings_html,
                           roto=roto_html,
                           matchups=matchups)


@app.route("/current_season/payouts", methods=["GET", "POST"])
def current_season_payouts():
    db = get_db()
    db.execute(
        f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE season=?
            """, (CURRENT_SEASON,)
    ).fetchall()

    dollars = {
        "League Winner": 500,
        "League Runner Up": 250,
        "Roto Winner": 175,
        "Roto 2nd Place": 125,
        "Roto 3rd Place": 75,
        "#1 Seed in Playoffs": 60,
        "#2 Seed in Playoffs": 60,
        "#3 Seed in Playoffs": 60,
        "#4 Seed in Playoffs": 60,
        "#5 Seed in Playoffs": 60,
        "#6 Seed in Playoffs": 60,
        "Roto 4th Place": 25,
        "Roto 5th Place": 25,
        "Roto 6th Place": 25,
        "Roto 7th Place": 25,
        "Roto 8th Place": 25,
        "Roto 9th Place": 25,
        "Highest Single Game Score": 25,
        "Week 1 Winner": 10,
        "Week 2 Winner": 10,
        "Week 3 Winner": 10,
        "Week 4 Winner": 10,
        "Week 5 Winner": 10,
        "Week 6 Winner": 10,
        "Week 7 Winner": 10,
        "Week 8 Winner": 10,
        "Week 9 Winner": 10,
        "Week 10 Winner": 10,
        "Week 11 Winner": 10,
        "Week 12 Winner": 10,
        "Week 13 Winner": 10,
        "Week 14 Winner": 10,
    }

    payouts = pd.DataFrame(index=list(dollars.keys()), columns=[
                           "League Member", "Value", "Payout"])

    payouts["Payout"] = list(dollars.values())

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
            """, (CURRENT_SEASON,)
    ).fetchall()

    roto = get_roto(query)
    playoffs = get_playoffs(query)
    flag = ""
    if playoffs:
        weeks = list(playoffs.keys())
        weeks.sort()
        last_week = weeks[-1]
        if len(playoffs[last_week]) > 1:
            payouts.at["League Winner", "League Member"] = "--"
            payouts.at["League Runner Up", "League Member"] = "--"
        else:
            payouts.at["League Winner",
                       "League Member"] = playoffs[last_week][0]["winning_team"]
            payouts.at["League Runner Up",
                       "League Member"] = playoffs[last_week][0]["losing_team"]
        standings, ranks = get_standings(query)
        matchups = get_projected_playoff_teams(standings, ranks, roto, 6, 1)
        for i, seed in enumerate(matchups):
            key = f"#{i+1} Seed in Playoffs"

            # Convert "#1 First Last*" to "First Last"
            member = seed[3:].strip("*")
            payouts.at[key, "League Member"] = member

    else:
        flag = "*"
        payouts.at["#1 Seed in Playoffs", "League Member"] = "--"
        payouts.at["#2 Seed in Playoffs", "League Member"] = "--"
        payouts.at["#3 Seed in Playoffs", "League Member"] = "--"
        payouts.at["#4 Seed in Playoffs", "League Member"] = "--"
        payouts.at["#5 Seed in Playoffs", "League Member"] = "--"
        payouts.at["#6 Seed in Playoffs", "League Member"] = "--"

    roto_w_ranks = roto.reset_index().rename(columns={"index": "Member"})
    for key, value in roto_w_ranks.iterrows():
        if key == 0:
            helper = "Roto Winner"
        else:
            helper = f"Roto {ordinal(key+1)} Place"
        payouts.at[helper, "League Member"] = value["Member"] + flag
        payouts.at[helper, "Value"] = str(value["Total"]) + flag
        if key > 7:
            break

    week_winners = get_week_winners(query, 13)
    for index, winner in enumerate(week_winners):
        key = f"Week {index + 1} Winner"
        payouts.at[key, "League Member"] = week_winners[index][0]
        payouts.at[key, "Value"] = week_winners[index][1]
        if index == 13:
            break

    member_high_score, value = get_overall_highest(query)
    payouts.at["Highest Single Game Score",
               "League Member"] = str(member_high_score) + flag
    payouts.at["Highest Single Game Score", "Value"] = str(value) + flag

    payouts = payouts.fillna("--")

    league_members = get_league_members(query)
    owed = {}
    for member in league_members:
        owed[member] = 0
    for _, value in payouts.iterrows():
        winner = value["League Member"].strip("*")
        if winner != "--":
            owed[winner] += int(value["Payout"])

    owed = {k: v for k, v in sorted(
        owed.items(), key=lambda item: item[1], reverse=True)}

    return render_template("current_season_payouts.html",
                           payouts=payouts.to_html(
                               classes="table table-striped"),
                           owed=owed,
                           cards=CURRENT_SEASON_CARDS)


@app.route("/current_season/analytics", methods=["GET", "POST"])
def current_season_analytics():
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
            WHERE season=? AND playoffs=?
            """, (CURRENT_SEASON, 0)
    ).fetchall()

    roto_against = get_roto_against(query)
    head_to_head = get_head_to_head(query)
    intervals = get_intervals(query)

    return render_template("current_season_analytics.html",
                           cards=CURRENT_SEASON_CARDS,
                           roto_against=roto_against.to_html(
                               classes="table table-striped"),
                           head_to_head=head_to_head.to_html(
                               classes="table table-striped"),
                           intervals=intervals.to_html(classes="table table-striped"))


@app.route("/current_season/report", methods=["GET", "POST"])
def current_season_report():
    return render_template("current_season_report.html", cards=CURRENT_SEASON_CARDS)


@app.route("/current_season/power_rankings", methods=["GET", "POST"])
def current_season_power_rankings():
    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
    power_rankings_path = str(base_path) + "/*"
    reports = glob.glob(power_rankings_path)

    args = request.args
    try:
        week_of_current_report = args.get("week")
    except AttributeError as e:
        print("Something went wrong getting parameters!", e)

    if week_of_current_report == None:
        current_report_file = reports[-1]
        week_of_current_report = parse_rankings_filename(current_report_file)

    current_info, previous_info = get_power_rankings_infos(
        reports, week_of_current_report)

    if previous_info:
        for member in current_info.keys():
            current_info[member]["change"] = previous_info[member]["rank"] - \
                current_info[member]["rank"]

    form = selectPowerRankWeek()
    if form.validate_on_submit():
        return redirect(url_for('current_season_power_rankings', week=form.week.data))
    return render_template("current_season_power_rankings.html",
                           week=week_of_current_report,
                           current_info=current_info,
                           form=form,
                           cards=CURRENT_SEASON_CARDS)


@app.route("/current_season/announcements", methods=["GET", "POST"])
def current_season_announcements():
    return render_template("current_season_report.html", cards=CURRENT_SEASON_CARDS)


@app.route("/apis/power_rankings_available", methods=["GET", "POST"])
def get_power_rankings_available():
    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
    power_rankings_path = str(base_path) + "/*"
    reports = glob.glob(power_rankings_path)
    data = {}
    for report in reports:
        week = parse_rankings_filename(report)
        data[str(week)] = f"Week {week}"

    return jsonify(data)
