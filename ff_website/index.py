from flask import flash, redirect, render_template, url_for

from ff_website import app
from ff_website.apis import get_all_members
from ff_website.constants import *
from ff_website.db import get_db
from ff_website.forms import (CreateGame, CreateMember, GameQualities,
                              HeadToHead)


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


@app.route("/members/2", methods=["GET", "POST"])
def test():
    return render_template("user.html")


@app.route("/archives/", methods=["GET", "POST"])
def archives_home():
    return render_template("archives_home.html")


@app.route("/archives/head_to_head", methods=["GET", "POST"])
def h2h():
    form = HeadToHead()
    if form.validate_on_submit():
        print("succeeded")
    else:
        print("failed")

    return render_template("head_to_head.html", form=form)


@app.route("/archives/game_qualities", methods=["GET", "POST"])
def game_qualities():
    form = GameQualities()
    if form.validate_on_submit():
        print(form.data["filter"])
        print("succeeded")
    else:
        print("failed")
    return render_template("game_qualities.html", form=form)


@app.route("/tools/create_member", methods=["GET", "POST"])
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


@app.route("/tools/create_game", methods=["GET", "POST"])
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


@app.route("/apis/test", methods=["GET", "POST"])
def add_league_members():

    db = get_db()
    # sql_as_string = open(
    #     "C:\\Users\\gmfol\\Desktop\\IndProj\\ff_website\\ff_website\\members.sql").read()
    # db.executescript(sql_as_string)

    db.execute(
        """
        INSERT INTO member(
            first_name, last_name, year_joined, active)
            VALUES (?, ?, ?, ?)
        """,
        ("Garrett", "Folbe", 2016, 1)
    )
    db.commit()
