import glob
import json
import os
import requests
from datetime import datetime
from pathlib import Path

import inflect
import pandas as pd
from flask import flash, jsonify, redirect, render_template, request, url_for, send_file
from flask_login import (UserMixin, current_user, login_required, login_user,
                         logout_user)
from PIL import Image
from pytz import timezone

from werkzeug.utils import secure_filename

from ff_website import app, bcrypt
from ff_website.apis import get_member_id
from ff_website.constants import *
from ff_website.credentials import accepted_admins, cookies
from ff_website.db import close_db, get_db
from ff_website.forms import (CreateGame, CreateMember, CreatePowerRankings,
                              GameQualities, HeadToHead, JarrettReport,
                              LoginForm, MakeAnnouncement, RegistrationForm,
                              SeasonSelector, SelectPowerRankWeek, changePassword)
from ff_website.helper_functions import *


class User(UserMixin):
    def __init__(self, id, username, email, password, admin_privileges, announcement_privileges):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.admin_privileges = admin_privileges
        self.announcement_privileges = announcement_privileges
        self.authenticated = False

    def __repr__(self):
        return f"{self.username}, admin_privileges: {self.admin_privileges}, announcement_privileges: {self.announcement_privileges}"

    def is_active(self):
        return self.is_active()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return True

    def get_id(self):
        return self.id


@app.login_manager.user_loader
def load_user(user_id):
    with get_db() as db:
        lu = db.execute(
            f"""
        SELECT * from user
        WHERE {USER_ID}=?
        """, (user_id,)
        ).fetchone()
    close_db()
    if lu is None:
        return None
    else:
        return User(id=lu[USER_ID],
                    username=lu[USERNAME],
                    email=lu[EMAIL],
                    password=lu[PASSWORD],
                    admin_privileges=lu[ADMIN_PRIVILEGES],
                    announcement_privileges=lu[ANNOUNCEMENT_PRIVILEGES]
                    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def api_error(e):
    return render_template('404.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        logout_user()

    db = get_db()
    form = RegistrationForm()
    if form.validate_on_submit():
        inputted_username = form.username.data
        inputted_email = form.email.data

        query = db.execute(
            f"""
            SELECT * FROM user
            WHERE {USERNAME}=? OR {EMAIL}=?
            """, (inputted_username, inputted_email)
        ).fetchone()
        if query:
            if query[USERNAME] == inputted_username:
                form.username.errors.append("That username is already taken")
            if query[EMAIL] == inputted_email:
                form.email.errors.append(
                    "That email address is already being used by another account")
        else:
            hashed_password = bcrypt.generate_password_hash(
                form.password.data).decode('utf-8')
            admin_privileges = 0
            announcement_privileges = 0
            if form.username.data in accepted_admins:
                admin_privileges = 1
                announcement_privileges = 1

            db.execute(
                f"""
                INSERT INTO user
                ({USERNAME}, {EMAIL}, {PASSWORD}, {
                 ADMIN_PRIVILEGES}, {ANNOUNCEMENT_PRIVILEGES})
                VALUES(?, ?, ?, ?, ?)
                """, (form.username.data, form.email.data, hashed_password, admin_privileges, announcement_privileges)
            )
            db.commit()
            id = db.execute(
                f"""
                SELECT {USER_ID} FROM user
                WHERE {USERNAME}=?
                """, (form.username.data,)
            ).fetchone()
            user = User(id=id[USER_ID],
                        username=form.username.data,
                        email=form.email.data,
                        password=hashed_password,
                        admin_privileges=admin_privileges,
                        announcement_privileges=announcement_privileges)
            login_user(user)
            close_db()
            return redirect(url_for('homepage'))

    close_db()
    return render_template("register.html", form=form, title="Register")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    db = get_db()
    if form.validate_on_submit():
        query = db.execute(
            f"""
            SELECT * FROM user
            WHERE {USERNAME}=? OR {EMAIL}=?
            """, (form.username_or_email.data, form.username_or_email.data)
        ).fetchone()
        if query:
            if bcrypt.check_password_hash(query[PASSWORD], form.password.data):
                user = User(id=query[USER_ID], username=query[USERNAME],
                            email=query[EMAIL], password=query[PASSWORD],
                            admin_privileges=query[ADMIN_PRIVILEGES],
                            announcement_privileges=query[ANNOUNCEMENT_PRIVILEGES])
                login_user(user)
                close_db()
                return redirect(url_for('homepage'))
            else:
                form.password.errors.append("Password is incorrect")

        else:
            form.username_or_email.errors.append(
                "No account is associated with that username or email address")

    close_db()
    return render_template('login.html', form=form, title="Login")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    flash("You have logged out", "info")
    return redirect(url_for("login"))


@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if current_user.username == "admin":
        flash("Password cannot be updated for admin", "danger")
        return redirect(url_for('home'))

    form = changePassword()
    if form.validate_on_submit():
        current_username = current_user.username

        db = get_db()
        query = db.execute(
            f"""
            SELECT {PASSWORD} from user
            WHERE {USERNAME}=?
            """, (current_username,)
        ).fetchone()
        correct_current_password = query[PASSWORD]
        if not bcrypt.check_password_hash(correct_current_password, form.current_password.data):
            form.current_password.errors.append(
                "Current password is incorrect")
        else:
            new_password = bcrypt.generate_password_hash(
                form.new_password.data)
            db.execute(
                f"""
                UPDATE user
                SET {PASSWORD}=?
                WHERE {USERNAME}=?
                """, (new_password, current_username)
            )
            db.commit()
            flash("Password updated!", "success")
            return redirect(url_for('change_password'))

    close_db()
    return render_template("change_password.html", form=form)


@app.route("/", methods=["GET", "POST"])
def homepage():
    links = [
        {
            "title": "League Members",
            "img_file": url_for("static", filename="img/league_members.png"),
            "description": "Find more information on this current season, including: standings, statistics, and more.",
            "link": url_for("members")
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
            "description": "View the names of the enshrined members of our league who have etched their names in the history books.",
            "link": url_for("hall_of_fame")
        },
        {
            "title": "League Office",
            "img_file": url_for("static", filename="img/espn.png"),
            "description": "Visit our official home page on ESPN for your complete fantasy football experience.",
            "link": "https://fantasy.espn.com/football/league?leagueId=50890012&seasonId=2024"
        }
    ]
    return render_template("home.html", ql=links, title="Home")


@app.route("/members", methods=["GET", "POST"])
def members():
    db = get_db()
    data = db.execute(
        f"""
        SELECT * FROM member
        WHERE {ACTIVE}=?
        ORDER BY {LAST_NAME} ASC
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

    close_db()
    return render_template("league_members.html", title="Current Members", cards=cards)


@app.route("/tools", methods=["GET", "POST"])
@login_required
def tools():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    return render_template("tools.html", title="Tools")


@app.route("/tools/list_all_members", methods=["GET", "POST"])
@login_required
def list_members():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    all_members = db.execute(
        """
        SELECT * FROM member
        """
    ).fetchall()
    close_db()
    data = jsonify_members(all_members)
    return render_template("members_admin.html", data=data, title="Members Admin")


@app.route("/tools/update_member/<int:member_id>", methods=["GET", "POST"])
@login_required
def update_member(member_id):

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    info = db.execute(
        """
        SELECT * from member WHERE
        member_id=?
        """, (member_id,)
    ).fetchone()

    original_first_name = info[FIRST_NAME]
    original_last_name = info[LAST_NAME]
    original_year_joined = info[YEAR_JOINED]
    original_activity_status = info[ACTIVE]
    original_image_path = info[IMG_FILEPATH]

    form = CreateMember(firstName=original_first_name,
                        lastName=original_last_name,
                        initialYear=str(original_year_joined),
                        activeMember=str(original_activity_status))

    if form.validate_on_submit():
        if form.firstName.data == original_first_name and \
                form.lastName.data == original_last_name and \
                form.initialYear.data == str(original_year_joined) and \
                form.activeMember.data == str(original_activity_status) and \
                form.image.data == None:
            flash('Member not changed.', 'warning')
            close_db()
            return redirect(url_for('list_members'))
        else:
            new_first_name = form.firstName.data
            new_last_name = form.lastName.data
            new_year_joined = int(form.initialYear.data)
            new_status = int(form.activeMember.data)

            photo = form.data["image"]
            file_name = original_image_path
            if photo:
                original_first_name = form.data["firstName"]
                original_last_name = form.data["lastName"]
                extension = os.path.splitext(photo.filename)[1]
                file_name = f"{original_first_name}_{original_last_name}{extension}"
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
            close_db()
            flash('Member updated!', 'success')
            return redirect(url_for('tools'))

    return render_template("update_member.html",
                           form=form,
                           first_name=original_first_name,
                           last_name=original_last_name,
                           year_joined=original_year_joined,
                           status=original_activity_status,
                           title="Update a Member")


@app.route("/tools/delete_member/<int:member_id>", methods=["GET", "POST"])
@login_required
def delete_member(member_id):

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

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
    close_db()
    flash('Member deleted!', 'danger')
    return redirect(url_for('tools'))


@app.route("/tools/list_all_seasons", methods=["GET", "POST"])
@login_required
def list_all_seasons():
    db = get_db()
    query = db.execute(
        f"""
        SELECT DISTINCT {SEASON}
        FROM game
        """
    )
    seasons = [x[SEASON] for x in query]
    close_db()
    return render_template("list_all_seasons.html", seasons=seasons, title="All Seasons")


@app.route("/tools/list_all_games/<string:season>", methods=["GET", "POST"])
@login_required
def list_games(season):

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    all_games = db.execute(
        f"""
        SELECT game_id, team_A_id, team_B_id, team_A_score, team_B_score, season, week, matchup_length, playoffs,
        t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name
        FROM game
        INNER JOIN member t2
        ON t2.member_id = team_A_id
        INNER JOIN member t3
        ON t3.member_id = team_B_id
        WHERE {SEASON}=?
        ORDER BY 
        {SEASON} ASC,
        {WEEK} ASC
        """, (season,)
    ).fetchall()
    df = pd.DataFrame(columns=["id", "Season", "Week", "Playoffs",
                               "Team_A_id", "Team_A_name", "Team_A_score", "Team_B_id", "Team_B_name", "Team_B_score", "Edit", "Delete"])

    for index, element in enumerate(all_games):
        df.loc[index] = [
            element[GAME_ID],
            element[SEASON],
            element[WEEK],
            element[PLAYOFFS],
            element[TEAM_A_ID],
            element["team_A_first_name"] + " " + element["team_A_last_name"],
            element[TEAM_A_SCORE],
            element[TEAM_B_ID],
            element["team_B_first_name"] + " " + element["team_B_last_name"],
            element[TEAM_B_SCORE],
            "Placeholder",
            "Placeholder"
        ]

    close_db()
    return render_template("games_admin.html", df=df, title=f"{season} Games")


@app.route("/tools/update_game/<int:game_id>", methods=["GET", "POST"])
@login_required
def update_game(game_id):

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

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
            close_db()
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
            close_db()
            flash('Game updated!', 'success')
            close_db()
            return redirect(url_for('tools'))

    return render_template("update_game.html", form=form, title="Update Game")


@app.route("/tools/delete_game/<int:game_id>", methods=["GET", "POST"])
@login_required
def delete_game(game_id):

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    db.execute(
        """
        DELETE FROM game
        WHERE game_id=?
        """, (game_id,)
    )
    db.commit()
    close_db()
    flash('Game deleted!', 'danger')
    return redirect(url_for('tools'))


@app.route("/tools/create_member", methods=["GET", "POST"])
@login_required
def create_member():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    form = CreateMember()
    if form.validate_on_submit():
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
            close_db()
            flash('Member created!', 'success')
            return redirect(url_for('tools'))

    close_db()
    return render_template("create_member.html", form=form, title="Create a Member")


@app.route("/tools/create_game", methods=["GET", "POST"])
@login_required
def create_game():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()

    form = CreateGame()
    if form.validate_on_submit():
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
            close_db()
            flash('Game created!', 'success')
            return redirect(url_for('create_game'))

    close_db()
    return render_template("create_game.html", form=form, title="Create a Game")


@app.route("/tools/add_all_members", methods=["GET", "POST"])
@login_required
def add_league_members():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()

    # Clear table
    db.execute(
        """
        DELETE FROM member
        """
    )

    members = json.load(open(os.path.join("ff-website", "data", member_data, "r")))

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

    close_db()
    return jsonify(members)


@app.route("/tools/add_all_games", methods=["GET", "POST"])
@login_required
def add_games():
    # Hard coded so that we can load data for years if there's no existing data
    seasons = [x for x in range(2017, CURRENT_SEASON + 1)]

    return render_template("fetch_season_data_selector.html", seasons=seasons, title="Add all Games")


@app.route("/tools/create_power_rankings", methods=["GET", "POST"])
@login_required
def create_power_rankings():

    if not current_user.admin_privileges:
        return redirect(url_for('homepage'))

    db = get_db()
    actives_query = db.execute(
        f"""
        SELECT {MEMBER_ID} FROM member
        WHERE {ACTIVE}=?
        """, (1,)
    ).fetchall()

    form = CreatePowerRankings(year=CURRENT_SEASON)
    if form.validate_on_submit():
        base_path = os.path.join(
            app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
        files = glob.glob(base_path + "/*")
        for file in files:
            if str(parse_rankings_filename(file)) == str(form.week.data):
                form.week.errors.append(
                    "A power rankings for that week already exists for the current season. Please delete it before proceeding")
                return render_template("create_power_rankings.html", form=form)

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
            week = form.week.data
            file_name = f"{CURRENT_SEASON}_power_rankings_week_{week}.json"

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
                "year": CURRENT_SEASON,
                "week": week,
                "rankings": [names_dict[int(i)] for i in submitted]
            }

            file_path = os.path.join(
                app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
            os.makedirs(file_path, exist_ok=True)
            json.dump(object, open(os.path.join(file_path, file_name), "w"))
            flash('Power Rankings Created!', 'success')
            close_db()
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
                "The following members weren't present: " + names_str)
            flash('Power Rankings Failed to Create!', 'danger')

    close_db()
    return render_template("create_power_rankings.html", form=form, title="Create Power Rankings")


@app.route("/tools/list_all_power_rankings", methods=["GET", "POST"])
@login_required
def list_all_power_rankings():
    if current_user.admin_privileges != 1:
        return redirect(url_for('homepage'))

    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
    power_rankings_path = str(base_path) + "/*"
    reports = glob.glob(power_rankings_path)

    files = [
        {
            "filename": os.path.basename(report),
            "week": parse_rankings_filename(report),
            "season": CURRENT_SEASON
        }
        for report in reports
    ]

    return render_template("power_rankings_admin.html", files=files, title="Power Rankings Admin")


@app.route("/tools/delete_power_ranking", methods=["GET", "POST"])
def delete_power_ranking():
    if current_user.admin_privileges != 1:
        return redirect(url_for('homepage'))

    args = request.args
    season = None
    week = None
    try:
        season = args.get("season")
        week = args.get("week")
    except AttributeError:
        print("Something went wrong getting args!")

    filename = f"{season}_power_rankings_week_{week}.json"
    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(season), filename
    )

    if os.path.exists(base_path):

        os.remove(base_path)
        flash("Power rankings deleted!", "danger")
    else:
        flash("Power rankings could not be deleted", "warning")

    return redirect(url_for('list_all_power_rankings'))


@app.route("/tools/create_jarrett_report", methods=["GET", "POST"])
@login_required
def create_jarrett_report():
    if current_user.admin_privileges == 0:
        return redirect(url_for('homepage'))

    form = JarrettReport()
    if form.validate_on_submit():
        file_name = f"jarrett_report_{form.season.data}_{form.week.data}.pdf"
        base_path = os.path.join(app.root_path, "static", "jarrett_reports")

        os.makedirs(base_path, exist_ok=True)
        
        db = get_db()
        query = db.execute(
            f"""
            SELECT report_id
            FROM report
            WHERE {SEASON}=? AND {WEEK}=?
            """, (form.season.data, form.week.data)
        ).fetchone()
        
        if query:
            form.season.errors.append(
                "A report at this season/week already exists"
            )
            form.week.errors.append(
                "A report at this season/week already exists"
            )
            flash('Report not created', 'danger')
            return render_template("create_jarrett_report.html", form=form, title="Create Jarrett Report")
        
        else:
            secured_file = secure_filename(file_name)
            form.report.data.save(os.path.join(app.root_path, "static", "jarrett_reports", secured_file))
            db.execute(
                f"""
                INSERT INTO report
                ({TITLE}, {SEASON}, {WEEK}, {STATIC_URL})
                VALUES(?, ?, ?, ?)
                """, (form.title.data, form.season.data, form.week.data, f"jarrett_reports/{file_name}")
            )
            db.commit()
            flash('Jarrett Report Created!', 'success')

    return render_template("create_jarrett_report.html", form=form, title="Create Jarrett Report")


@ app.route("/tools/delete_jarrett_report", methods=["GET", "POST"])
@ login_required
def delete_jarrett_report():

    if current_user.admin_privileges == 0:
        return redirect(url_for('homepage'))

    args = request.args
    season = None
    week = None
    try:
        season = args.get("season")
        week = args.get("week")
    except AttributeError:
        print("Something went wrong getting args!")
        
    filename = f"jarrett_report_{season}_{week}.pdf"
    base_path = os.path.join(
        app.root_path, "static", "jarrett_reports", filename
    )

    if os.path.exists(base_path):
        os.remove(base_path)
        flash("Report deleted!", "danger")
        
        db = get_db()
        db.execute(
            f"""
            DELETE FROM report
            WHERE {SEASON}=? AND {WEEK}=?
            """, (season, week)
        )
        db.commit()
    else:
        flash("Report could not be deleted", "warning")

    return redirect(url_for('archived_reports'))

@ app.route("/tools/list_all_users")
@ login_required
def list_all_users():
    db = get_db()
    query = db.execute(
        f"""
        SELECT {USERNAME}, {USER_ID}, {ADMIN_PRIVILEGES}, {ANNOUNCEMENT_PRIVILEGES} FROM user
        WHERE {USERNAME} NOT IN {tuple(set(accepted_admins))}
        """
    ).fetchall()
    data = []
    for row in query:
        data.append({
            "user_id": row[USER_ID],
            "username": row[USERNAME],
            "admin_priv": row[ADMIN_PRIVILEGES],
            "announce_priv": row[ANNOUNCEMENT_PRIVILEGES]
        })

    return render_template("users_admin.html", data=data, title="Users Admin")


@app.route("/tools/grant_admin_status/<int:user_id>")
@login_required
def grant_admin_status(user_id):
    db = get_db()
    db.execute(
        f"""
        UPDATE user
        SET {ADMIN_PRIVILEGES}=?, {ANNOUNCEMENT_PRIVILEGES}=?
        WHERE {USER_ID}=?
        """, (1, 1, user_id)
    )
    db.commit()
    close_db()
    return redirect(url_for('list_all_users'))


@app.route("/tools/revoke_admin_status/<int:user_id>")
@login_required
def revoke_admin_status(user_id):
    db = get_db()
    db.execute(
        f"""
        UPDATE user
        SET {ADMIN_PRIVILEGES}=?
        WHERE {USER_ID}=?
        """, (0, user_id)
    )
    db.commit()
    close_db()
    return redirect(url_for('list_all_users'))


@app.route("/tools/grant_announcement_status/<int:user_id>")
@login_required
def grant_announcement_status(user_id):
    db = get_db()
    db.execute(
        f"""
        UPDATE user
        SET {ANNOUNCEMENT_PRIVILEGES}=?
        WHERE {USER_ID}=?
        """, (1, user_id)
    )
    db.commit()
    close_db()
    return redirect(url_for('list_all_users'))


@app.route("/tools/revoke_announcement_status/<int:user_id>")
@login_required
def revoke_announcement_status(user_id):
    db = get_db()
    db.execute(
        f"""
        UPDATE user
        SET {ANNOUNCEMENT_PRIVILEGES}=?
        WHERE {USER_ID}=?
        """, (0, user_id)
    )
    db.commit()
    close_db()
    return redirect(url_for('list_all_users'))


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

    active = "Active" if member_info[ACTIVE] == True else "Inactive"

    rookie = year_joined == CURRENT_SEASON

    all_games_for_member = db.execute(
        f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.year_joined
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE team_A_id=? OR team_B_id=?
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC

        """, (member_id, member_id)
    ).fetchall()

    all_games = db.execute(
        f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.year_joined
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
        """
    ).fetchall()

    if rookie:
        last_year = CURRENT_SEASON
    else:
        last_year = all_games_for_member[-1][SEASON]

    record, po_record, _, _, _, _ = get_overall_record(
        all_games_for_member, name)
    playoff_appearances = get_playoff_appearances(all_games_for_member)

    total_points, longest_win_streak, longest_losing_streak, most_points, fewest_points = get_additional_stats(
        all_games_for_member, name)

    if not all_games_for_member:
        total_points_str = "0.0"
    else:
        total_points_str = "{:.2f}".format(total_points)

    if not all_games_for_member:
        avg_points_str = "0.0"
    else:
        avg_points_str = "{:.2f}".format(
            total_points/len(all_games_for_member))

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
    seasons = get_schedules(all_games_for_member, name)

    summaries_html = summaries.to_html(
        classes="table table-striped") if not summaries.empty else None

    close_db()
    return render_template("member.html",
                           name=name,
                           img_filepath=img_filepath,
                           year_joined=year_joined,
                           status=active,
                           last_year=last_year,
                           playoff_appearances=playoff_appearances,
                           championships=championships,
                           cards=cards,
                           summaries=summaries_html,
                           seasons=seasons,
                           title=name)


@app.route("/archives/", methods=["GET", "POST"])
def archives_home():
    return render_template("archives_home.html", title="Archives")


@app.route("/archives/head_to_head", methods=["GET", "POST"])
def h2h():

    # Initialize variables that will be returned on successful submission of the form
    # If we do not make the variables None-types, the template cannot be rendered
    member_one_name, member_two_name, member_one_img, member_two_img, series_winner_name, num_matchups, num_times, series_split, tied, num_playoff_matchups, num_regular_matchups, streak_count, streak_holder = None, None, None, None, None, None, None, None, None, None, None, None, None

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

    db = get_db()
    # If we got the members successfully, find the history of their games
    if member_one_id and member_two_id:
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "Winning Team", "Losing Team", "Score"])

        query = db.execute(
            f"""
            SELECT team_A_score, team_B_score, season, week, matchup_length, playoffs,
            t2.first_name as team_A_first_name, t2.last_name as team_A_last_name, t2.img_filepath as team_A_img_filepath, t2.member_id as member_A_id,
            t3.first_name as team_B_first_name, t3.last_name as team_B_last_name, t3.img_filepath as team_B_img_filepath, t3.member_id as member_B_id
            FROM game
            INNER JOIN member t2
            ON t2.member_id = team_A_id
            INNER JOIN member t3
            ON t3.member_id = team_B_id
            WHERE team_A_id = ? AND team_B_id = ? OR team_A_id = ? AND team_B_id = ?
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """, (member_one_id, member_two_id,
                  member_two_id, member_one_id)
        ).fetchall()
        for row in query:
            if str(row["member_A_id"]) == str(member_one_id):
                member_one_img = row["team_A_img_filepath"]
                member_one_score = row["team_A_score"]
                member_one_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"

                member_two_img = row["team_B_img_filepath"]
                member_two_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"
                member_two_score = row["team_B_score"]

            else:
                member_one_img = row["team_B_img_filepath"]
                member_one_score = row["team_B_score"]
                member_one_name = f"{row['team_B_first_name']} {row['team_B_last_name']}"

                member_two_img = row["team_A_img_filepath"]
                member_two_name = f"{row['team_A_first_name']} {row['team_A_last_name']}"
                member_two_score = row["team_A_score"]

            total_points += (float(member_one_score) + float(member_two_score))

            season = row["season"]
            week = row["week"]
            matchup_length = row["matchup_length"]
            playoffs = row["playoffs"]

            winning_team = member_one_name if member_one_score > member_two_score else member_two_name
            losing_team = member_one_name if member_one_score < member_two_score else member_two_name

            winning_score = member_one_score if member_one_score > member_two_score else member_two_score
            losing_score = member_one_score if member_one_score < member_two_score else member_two_score
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
                """, (member_one_id, member_two_id)
            ).fetchall()
            if len(query) == 2:
                if str(query[0][MEMBER_ID]) == str(member_one_id):
                    member_one_img = query[0][IMG_FILEPATH]
                    member_one_name = f"{query[0][FIRST_NAME]} {query[0][LAST_NAME]}"

                    member_two_img = query[1][IMG_FILEPATH]
                    member_two_name = f"{query[1][FIRST_NAME]} {query[1][LAST_NAME]}"

                else:
                    member_one_img = query[1][IMG_FILEPATH]
                    member_one_name = f"{query[1][FIRST_NAME]} {query[1][LAST_NAME]}"

                    member_two_img = query[0][IMG_FILEPATH]
                    member_two_name = f"{query[0][FIRST_NAME]} {query[0][LAST_NAME]}"

    close_db()
    if form.validate_on_submit():
        return redirect(url_for("h2h", member_one_id=form.data["leagueMemberOne"], member_two_id=form.data["leagueMemberTwo"]))
    return render_template("head_to_head.html",
                           form=form,
                           team_A_name=member_one_name,
                           team_B_name=member_two_name,
                           team_A_img=member_one_img,
                           team_B_img=member_two_img,
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
                           matchups_exist=num_matchups != 0,
                           title="Head to Head"
                           )


@app.route("/archives/game_qualities", methods=["GET", "POST"])
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

    db = get_db()

    # Fewest points scored combined
    if filter_type == "1":
        total_scores_list = []
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

    # Fewest points scored individual
    if filter_type == "2":
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "League Member", "Points"])
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

    # Most points scored combined
    if filter_type == "3":
        total_scores_list = []
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

    # Fewest points scored combined
    if filter_type == "4":
        df = pd.DataFrame(columns=[
            "Season", "Week", "Matchup Format", "League Member", "Points"])
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

    # Largest margin of victory
    if filter_type == "5":
        deficits_list = []
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

    # Smallest margin of victory
    if filter_type == "6":
        deficits_list = []
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

    df.index += 1

    close_db()
    if form.validate_on_submit():
        return redirect(url_for("game_qualities", filter_type=form.data["filter"], num_results=form.data["numberOfResults"]))

    return render_template("game_qualities.html",
                           form=form,
                           query_specified=len(df.index != 0),
                           df=df.to_html(classes="table table-striped"),
                           title="Game Qualities")


@app.route("/archives/season_summary", methods=["GET", "POST"])
def season_summary():

    form = SeasonSelector()
    args = request.args
    year, standings, all_weeks, roto, playoffs, read_seasonal_league_settings = None, None, None, None, None, None

    standings = pd.DataFrame()
    roto = pd.DataFrame()

    try:
        year = args.get("year")
    except AttributeError as e:
        print("Something went wrong getting parameters", e)

    db = get_db()

    if year:
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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """, (year,)
        ).fetchall()

        standings, _ = get_standings(query)
        playoffs = get_playoff_results_for_season_summary(
            query, NUM_PLAYOFF_TEAMS_PER_YEAR[int(year)])
        all_weeks = get_all_week_results(query)
        roto = get_roto(query)

        read_seasonal_league_settings = json.load(open(os.path.join(
            app.root_path, "data", "season_settings_archives", f"{year}_season_settings.json")))

    if form.validate_on_submit():
        close_db()
        return redirect(url_for("season_summary", year=form.data["year"]))

    close_db()
    return render_template("season_summary.html",
                           form=form,
                           year=year,
                           season_settings=read_seasonal_league_settings,
                           all_weeks=all_weeks,
                           roto=roto.to_html(classes="table table-striped"),
                           playoffs=playoffs,
                           standings=standings.to_html(
                               classes="table table-striped"),
                           title="Season Summary")


@app.route("/archives/inactive_members", methods=["GET", "POST"])
def inactive_members():
    db = get_db()
    data = db.execute(
        f"""
        SELECT * FROM member
        WHERE {ACTIVE}=?
        ORDER BY {LAST_NAME} ASC
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

    close_db()
    return render_template("league_members.html", title="Inactive Members", cards=cards)


@app.route("/archives/archived_reports", methods=["GET", "POST"])
def archived_reports():
    
    db = get_db()
    reports = db.execute(
        f"""
        SELECT {WEEK}, {SEASON}, {TITLE}, {STATIC_URL}
        FROM report
        ORDER BY {SEASON} DESC, {WEEK} ASC
        """
    )
    archived_reports = {}
    for row in reports:
        season = row[SEASON]
        if season not in archived_reports:
            archived_reports[season] = [{
                "week" : row[WEEK],
                "season": row[SEASON],
                "title" : row[TITLE],
                "file_name" : row[STATIC_URL]
            }]
        else:
            archived_reports[season].append({
                "week" : row[WEEK],
                "season": row[SEASON],
                "title" : row[TITLE],
                "file_name" : row[STATIC_URL]
            })     
    
    return render_template("archived_reports.html",
                           archived_reports=archived_reports,
                           title="Archived Jart Reports🌽"
                           )


@app.route("/archives/league_gatherings", methods=["GET"])
def league_gatherings():
    
    data = [
        {
            "image" : "thanksgiving_2021.jpg",
            "date" : "Wednesday, November 24th, 2021",
            "location" : "Royal Oak, MI",
            "description" : """
                The first annual edition of the league's Drinksgiving pregame took place at Noah's new apartment in Royal Oak.
                Our gracious host laid out a few Oreos to satisfy our appetites, and Dmichs provided illegally imported Israeli alcohol. 
                Boogie Fever capped the night off, where a reserved table sat empty all night.
                """
        },
        {
            "image" : "thanksgiving_2022.jpg",
            "date" : "Wednesday, November 23rd, 2022",
            "location" : "Royal Oak, MI",
            "description" : """ 
            The night began in Jason's new condo at an hour so early, some of us were still working.
            The league quickly relocated to Dick O' Dow's where some members were savvy enough to cut the heniously long line.
            Others weren't as lucky, which resulted in a league divided after some pushed to Social.
            """
        },
        {
            "image" : "thanksgiving_2023.jpg",
            "date" : "Wednesday, November 22nd, 2023",
            "location" : "Royal Oak, MI",
            "description" : """
            In 2023, Garrett and Brad became the 3rd and 4th members to host a Drinksgiving pregame, this time in their new 
            apartment in downtown Royal Oak. The ratio may have been bad, and our glue guy was missing, but the mini hot dogs
            and little bites kept morale high. The night ended at Dick O' Dow's (for some at a later hour than others)
            for a second consecutive year, though the fire marshall wasn't for the boys that night, 
            restricting some league members to the front room.
            """
        },
        {
            "image": "tinroof.jpg",
            "date": "Friday, June 14th, 2024",
            "location": "Detroit, MI",
            "description": """
            The league celebrated Merrick Bank returning to the Detroit area by helping him break in his (and Alexa's) new apartment in
            Downtown Detroit.  After the pregame, the group relocated to Tin Roof, followed by Deluxx Fluxx. Despite Jason and 
            Garrett's best efforts at foosball, the night took an unexpected turn when our guest, Michael Kunz, decided to 
            fight a street sign outside of the bar, cutting his head. The allegations of half of the group getting removed from 
            the club remain unproven.
            """
        },
        {
            "image": "july_4th_2024.jpg",
            "date": "Thursday, July 4th, 2024",
            "location": "Keego Harbor, MI",
            "description": """
            With Merrick Weingarten out of the country on our nation's birthday, Merrick Bank answered the call of our boating
            needs by hosting us in his parents' new lakehouse. After braving the choppy waters of Sylvan Lake, the gang indulged 
            in a never-ending barrage of food, highlighted by our boat captain cheffing it up on the grill with some burgers, dogs,
            and a suspiciously large amount of Leo's chili.
            """
        },
        {
            "image": "nola.jpg",
            "date": "Saturday, August 31st, 2024",
            "location": "New Orleans, LA",
            "description": """
            The league's first group trip finally took place in the great city of New Orleans. Highlighted by a seafood boil (pictured),
            nights on the town on Bourbon Street, a campus tour of Tulane University, and a semi-live draft, the gang enjoyed eachother's 
            company in the Big Easy.
            """
        },
        {
            "image": "MB_engagement.jpg",
            "date": "Sunday, November 17th, 2024",
            "location": "New York City, NY",
            "description": """
            Merrick Bank became first member of the league to pop the question, proposing to his high school sweetheart, Alexa, in Central
            Park. To celebrate, our league's New York City coalition (including newly relocated Brad), joined him for drinks and festivities.
            Mazel Tov to the Banks! 🥂 
            """
        },
        {
            "image": "thanksgiving_2024.jpg",
            "date": "Sunday, November 27th, 2024",
            "location": "Royal Oak, MI",
            "description": """
            9 league members! Count 'em! This year's annual Drinksgiving pregame, graciously hosted by our resident Noogler, Jason Silverstone, saw 
            a record breaking number of league members attend, the most in one spot since our college days. In fact, the league had such a good time 
            together that we stayed as Jason's spot for the entire night, forgoing the usual bar push.
            """
        },
        {
            "image": "july_4th_2025.jpg",
            "date": "Friday, July 4th, 2025",
            "location": "Bloomfield Hills, MI",
            "description": """
            After a 2 year hiatus, the league returned to Upper Long Lake to enjoy a picture-perfect day on the water. Despite some nautical 
            malfunctions, new friends were made from both Cincinnati and New York City, bonding over a love for our great nation and consuming 
            festive, tri-colored Jell-O shots. The night was capped off with volleyball (Julia Kalugar, MVP) and a barbecue (Cindy Weingarten, MVP).
            """
        }
    ]
        
    return render_template("league_gatherings.html", 
                           title="League Gatherings",
                           data=data)


@app.route("/current_season", methods=["GET", "POST"])
def current_season():
    return render_template("current_season.html", cards=CURRENT_SEASON_CARDS, title="Current Season")


@app.route("/current_season/season_info", methods=["GET", "POST"])
def current_season_info():
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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """, (CURRENT_SEASON,)
    ).fetchall()

    current_members_query = db.execute(
        f"""
        SELECT {FIRST_NAME}, {LAST_NAME}
        FROM member
        WHERE {ACTIVE}=?
        ORDER BY
        {LAST_NAME} ASC
        """, (1,)
    ).fetchall()

    current_member_names = [
        f"{row['first_name']} {row['last_name']}" for row in current_members_query]

    standings, ranks = get_standings(query, current_member_names)
    standings_html = standings.to_html(classes="table table-striped")
    all_weeks = get_all_week_results(query)
    playoffs = get_playoff_results_for_season_summary(
        query, NUM_PLAYOFF_TEAMS_PER_YEAR[int(CURRENT_SEASON)])

    roto = get_roto(query, current_member_names)
    roto_html = roto.to_html(classes="table table-striped")

    matchups = get_projected_playoff_teams(standings, ranks, roto, 6, 2)

    if not query:
        matchups = [""] * NUM_PLAYOFF_TEAMS_PER_YEAR[int(CURRENT_SEASON)]

        matchups[0] = "Head to Head 1st Place"
        matchups[1] = "Head to Head 2nd Place"
        matchups[2] = "Head to Head 3rd Place"
        matchups[3] = "Head to Head 4th Place"
        matchups[4] = "Roto Wildcard #1"
        matchups[5] = "Roto Wildcard #2"

    close_db()
    return render_template("current_season_info.html",
                           year=CURRENT_SEASON,
                           cards=CURRENT_SEASON_CARDS,
                           standings=standings_html,
                           roto=roto_html,
                           matchups=matchups,
                           all_weeks=all_weeks,
                           playoffs=playoffs,
                           title="Current Season Info")


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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """, (CURRENT_SEASON,)
    ).fetchall()

    dollars = {
        "League Winner": 1200,
        "League Runner Up": 200,
        "Roto Winner": 300,
        "Roto 2nd Place": 60,
        "Roto 3rd Place": 20,
        "#1 Seed in Playoffs": 75,
        "#2 Seed in Playoffs": 65,
        "#3 Seed in Playoffs": 55,
        "#4 Seed in Playoffs": 45,
        "#5 Seed in Playoffs": 25,
        "#6 Seed in Playoffs": 15,
        "Highest Single Game Score": 60,
        "Week 1 Winner": 20,
        "Week 2 Winner": 20,
        "Week 3 Winner": 20,
        "Week 4 Winner": 20,
        "Week 5 Winner": 20,
        "Week 6 Winner": 20,
        "Week 7 Winner": 20,
        "Week 8 Winner": 20,
        "Week 9 Winner": 20,
        "Week 10 Winner": 20,
        "Week 11 Winner": 20,
        "Week 12 Winner": 20,
        "Week 13 Winner": 20,
        "Week 14 Winner": 20,
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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
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
        matchups = get_projected_playoff_teams(standings, ranks, roto, 6, 2)
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
        if key > 1: # number of roto teams included + 2 (Awful way to do this)
            break

    week_winners = get_week_winners(query, 13)
    for index, winner in enumerate(week_winners):
        key = f"Week {index + 1} Winner"
        payouts.at[key, "League Member"] = week_winners[index][0]
        payouts.at[key, "Value"] = week_winners[index][1]
        if index == 13:
            break

    member_high_score, value = get_overall_highest(query)
    if value > 0:
        payouts.at["Highest Single Game Score",
                   "League Member"] = str(member_high_score) + flag
        payouts.at["Highest Single Game Score", "Value"] = str(value) + flag

    payouts = payouts.fillna("--")

    league_members = get_league_members(query)

    # This implies the offseason
    if not league_members:
        current_members_query = db.execute(
            f"""
            SELECT {FIRST_NAME}, {LAST_NAME}
            FROM member
            WHERE {ACTIVE}=?
            ORDER BY
            {LAST_NAME} ASC
            """, (1,)
        ).fetchall()

        league_members = [
            f"{row['first_name']} {row['last_name']}" for row in current_members_query]

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
                           year=CURRENT_SEASON,
                           payouts=payouts.to_html(
                               classes="table table-striped"),
                           owed=owed,
                           cards=CURRENT_SEASON_CARDS,
                           title="Current Season Payouts")


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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """, (CURRENT_SEASON, 0)
    ).fetchall()

    current_members_query = db.execute(
        f"""
        SELECT {FIRST_NAME}, {LAST_NAME}
        FROM member
        WHERE {ACTIVE}=?
        ORDER BY
        {LAST_NAME} ASC
        """, (1,)
    ).fetchall()

    current_member_names = [
        f"{row['first_name']} {row['last_name']}" for row in current_members_query]
    
    roto_against = get_roto_against(query, current_member_names)
    head_to_head = get_head_to_head(query, current_member_names)
    intervals = get_intervals(query, current_member_names)

    close_db()
    return render_template("current_season_analytics.html",
                           year=CURRENT_SEASON,
                           cards=CURRENT_SEASON_CARDS,
                           roto_against=roto_against.to_html(
                               classes="table table-striped"),
                           head_to_head=head_to_head.to_html(
                               classes="table table-striped"),
                           intervals=intervals.to_html(
                               classes="table table-striped"),
                           title="Current Season Analytics")


@app.route("/current_season/report", methods=["GET", "POST"])
def current_season_report():
    db = get_db()
    
    reports = db.execute(
        f"""
        SELECT {WEEK}, {TITLE}, {STATIC_URL}
        FROM report
        WHERE {SEASON} = {CURRENT_SEASON}
        ORDER BY {WEEK} DESC
        """
    ).fetchall()
    
    data = []    
    for report in reports:
        data.append({
            "title": report[TITLE],
            "file_name": report[STATIC_URL],
            "week": report[WEEK]
        })
            
    current_report, season_reports = None, None
    
    if len(data) == 1:
        current_report = data[0]
    elif len(data) > 1:
        current_report = data[0]
        season_reports = data[1:]  
        
    return render_template("current_season_report.html",
                           current_report=current_report,
                           season_reports=season_reports,
                           cards=CURRENT_SEASON_CARDS,
                           title="The Jart Report🌽")


@app.route("/current_season/power_rankings", methods=["GET", "POST"])
def current_season_power_rankings():
    form = SelectPowerRankWeek()
    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
    power_rankings_path = str(base_path) + "/*"
    reports = glob.glob(power_rankings_path)

    if not reports:
        return render_template("current_season_power_rankings.html",
                               week=None,
                               current_info=None,
                               form=form,
                               cards=CURRENT_SEASON_CARDS
                               )

    helper = [(parse_rankings_filename(i), i) for i in reports]
    helper.sort(key=lambda x: int(x[0]))

    reports = [i[1] for i in helper]

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

    if form.validate_on_submit():
        return redirect(url_for('current_season_power_rankings', week=form.week.data))

    base_path = os.path.join(
        app.root_path, "data", "power_rankings", str(CURRENT_SEASON))
    power_rankings_path = str(base_path) + "/*"
    reports = glob.glob(power_rankings_path)

    reports.sort(key=lambda x: int(parse_rankings_filename(x)))

    graph_data = {}

    for report in reports:
        week = int(parse_rankings_filename(report))
        data = json.load(open(report, "r"))
        rankings = data["rankings"]
        for index, member in enumerate(rankings):
            if member not in graph_data:
                graph_data[member] = [(week, index + 1)]
            else:
                graph_data[member].append((week, index + 1))

    colors = ["lightCoral", "crimson", "hotPink", "orange", "gold", "indigo",
              "slateBlue", "greenYellow", "darkGreen", "dodgerBlue", "silver", "black"]

    all_data = []
    color_index = 0

    for member_name, data in graph_data.items():

        all_data.append(
            {
                "title": '"' + member_name + '"',
                "key": "".join(member_name.split()),
                "xvalues": [x[0] for x in data],
                "yvalues": [y[1] for y in data],
                "color": '"' + colors[color_index] + '"'
            }
        )

        color_index += 1

    all_data.sort(key=lambda x: x["title"].split(" ")[1][0])

    return render_template("current_season_power_rankings.html",
                           week=week_of_current_report,
                           current_info=current_info,
                           form=form,
                           cards=CURRENT_SEASON_CARDS,
                           title="Power Rankings",
                           all_data=all_data
                           )


@app.route("/current_season/announcements", methods=["GET", "POST"])
def current_season_announcements():
    db = get_db()
    query = db.execute(
        f"""
        SELECT {ANNOUNCEMENT_ID}, {TITLE}, {ANNOUNCEMENT}, {TIMESTAMP}, {USERNAME}
        FROM announcement
        INNER JOIN user
        ON {AUTHOR} = {USER_ID} 
        """
    ).fetchall()

    announcements = []
    for row in query:
        announcements.append({
            ANNOUNCEMENT_ID: row[ANNOUNCEMENT_ID],
            AUTHOR: row[USERNAME],
            TITLE: row[TITLE],
            ANNOUNCEMENT: row[ANNOUNCEMENT],
            TIMESTAMP: row[TIMESTAMP]
        })

    return render_template("current_season_announcements.html",
                           announcements=announcements,
                           cards=CURRENT_SEASON_CARDS,
                           title="Announcements")


@app.route("/current_season/create_announcement", methods=["GET", "POST"])
@login_required
def create_announcement():
    if current_user.announcement_privileges != 1:
        return redirect(url_for('current_season'))
    form = MakeAnnouncement()
    db = get_db()
    if form.validate_on_submit():
        tz = timezone('US/Eastern')
        cur_date = datetime.now(tz)
        timestamp = cur_date.strftime("%B %d, %Y %I:%M %p EST")

        db.execute(
            f"""
            INSERT INTO announcement
            ({TITLE}, {AUTHOR}, {ANNOUNCEMENT}, {TIMESTAMP})
            VALUES(?, ?, ?, ?)
            """, (form.title.data, current_user.id, form.announcement.data, timestamp)
        )
        db.commit()
        close_db()
        flash("Announcement created successfully!", "success")
        return redirect(url_for("current_season_announcements"))

    close_db()
    return render_template("create_announcement.html", form=form, title="Create Announcement")


@app.route("/current_season/delete_announcement/<int:announcement_id>", methods=["GET", "POST"])
@login_required
def delete_announcement(announcement_id):
    db = get_db()
    query = db.execute(
        f"""
        SELECT * FROM announcement
        WHERE {ANNOUNCEMENT_ID}=?        
        """, (announcement_id,)
    ).fetchone()
    if query:
        if str(query[AUTHOR]) == str(current_user.id) or current_user.admin_privileges == 1:
            db.execute(
                f"""
                DELETE FROM announcement
                WHERE {ANNOUNCEMENT_ID}=?
                """, (announcement_id,)
            )
            db.commit()
            close_db()
            flash('Announcement deleted', 'danger')
            return redirect(url_for('current_season_announcements'))

    close_db()
    return redirect(url_for('current_season_announcements'))


@app.route("/current_season/update_announcement/<int:announcement_id>", methods=["GET", "POST"])
@login_required
def update_announcement(announcement_id):
    if current_user.announcement_privileges != 1:
        return redirect(url_for('current_season'))
    db = get_db()
    query = db.execute(
        f"""
        SELECT * FROM announcement
        WHERE {ANNOUNCEMENT_ID}=?
        """, (announcement_id,)
    ).fetchone()
    current_title = query[TITLE]
    current_ann = query[ANNOUNCEMENT]

    form = MakeAnnouncement(
        title=current_title, announcement=current_ann)
    if form.validate_on_submit():
        db.execute(
            f"""
            UPDATE announcement
            SET {TITLE}=?, {ANNOUNCEMENT}=?
            WHERE {ANNOUNCEMENT_ID}=?
            """, (form.title.data, form.announcement.data, announcement_id)
        )
        db.commit()
        close_db()
        if form.title.data == current_title and form.announcement.data == current_ann:
            flash("Announcement unchanged", "warning")
        else:
            flash("Announcement updated", "warning")
        return redirect(url_for('current_season_announcements'))

    return render_template("update_announcement.html", form=form, title="Update Announcement")


@app.route("/hall_of_fame",  methods=["GET", "POST"])
def hall_of_fame():

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
            ORDER BY 
            {SEASON} ASC,
            {WEEK} ASC
            """
    ).fetchall()
    top_3_most_points_all_time, \
        top_3_most_points_single_season_excl_playoffs, \
        top_3_most_ppg_all_time, \
        top_3_most_appearances_overall, \
        top_3_most_wins_overall, \
        top_3_win_percentage_overall, \
        top_3_most_wins_single_season_excl_playoffs, \
        top_3_most_wins_single_season_incl_playoffs, \
        top_3_most_playoff_wins, \
        top_3_longest_win_streak, \
        top_3_most_roto_points_all_time, \
        top_3_most_top_scoring_weeks, \
        champions = hall_of_fame_helper(query)

    champion_cards = []
    for year, champion in champions.items():
        first_name, last_name = champion.split(" ")
        query = db.execute(
            f"""
            SELECT {IMG_FILEPATH} from member
            WHERE {FIRST_NAME}=? AND {LAST_NAME}=?
            """, (first_name, last_name)
        ).fetchone()
        img_src = query[IMG_FILEPATH]

        champion_cards.append({
            "name": champion,
            "year": year,
            "img_src": url_for('static', filename=f"img/avatars/{img_src}")
        })

    close_db()
    return render_template("hall_of_fame.html",
                           top_3_most_points_all_time=top_3_most_points_all_time,
                           top_3_most_ppg_all_time=top_3_most_ppg_all_time,
                           top_3_most_points_single_season_excl_playoffs=top_3_most_points_single_season_excl_playoffs,
                           top_3_most_appearances_overall=top_3_most_appearances_overall,
                           top_3_most_wins_overall=top_3_most_wins_overall,
                           top_3_win_percentage_overall=top_3_win_percentage_overall,
                           top_3_most_wins_single_season_excl_playoffs=top_3_most_wins_single_season_excl_playoffs,
                           top_3_most_wins_single_season_incl_playoffs=top_3_most_wins_single_season_incl_playoffs,
                           top_3_most_playoff_wins=top_3_most_playoff_wins,
                           top_3_longest_win_streak=top_3_longest_win_streak,
                           top_3_most_roto_points_all_time=top_3_most_roto_points_all_time,
                           top_3_most_top_scoring_weeks=top_3_most_top_scoring_weeks,
                           champions=champion_cards,
                           title="Hall of Fame"
                           )


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


@app.route("/apis/all_members", methods=["GET", "POST"])
def get_all_members():
    args = request.args
    active_arg = int(args.get("active"))
    db = get_db()

    if active_arg == 0:
        query = db.execute(
            f"""
            SELECT * FROM member
            WHERE {ACTIVE}=?
            ORDER BY {LAST_NAME} asc
            """, (0,)
        )

    elif active_arg == 1:
        query = db.execute(
            f"""
            SELECT * FROM member
            WHERE {ACTIVE}=?
            ORDER BY {LAST_NAME} asc
            """, (1,)
        )

    else:
        query = db.execute(
            f"""
            SELECT * FROM member
            ORDER BY {LAST_NAME} asc
            """
        )

    response = jsonify_members(query)

    close_db()
    return jsonify(response)


@login_required
@app.route("/apis/fetch_games", methods=["GET", "POST"])
def fetch_games():
    year, write = None, None

    args = request.args
    try:
        year = args.get("year")
        write = args.get("write") == "hard"
    except AttributeError as e:
        print("Something went wrong getting the args!", e)

    data_path = os.path.join(app.root_path, "data", f"{year}games.json")

    if year != str(CURRENT_SEASON):
        data = json.load(open(data_path, "r"))
    else:
        try:
            ID = league_IDs[year]

            # ESPN changed this for 2024 - not sure if it'll stay up or not
            base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{ID}"
            r = requests.get(url=base_url,
                             params={"view": "mMatchupScore"},
                             cookies=cookies)
            d = r.json()
            member_ids_path = os.path.join(
                app.root_path, "data", "member_ids.json")
            data = json.load(open(member_ids_path, "r"))
            member_ids = data[year]

            data = get_data_one_week_playoffs(d, member_ids, year)
            if write:
                json.dump(data, open(data_path, "w"), indent=4)

        except Exception as e:
            print("Something went wrong fetching new games!")
            data = []

    updates = []
    new_additions = []

    if data:
        for game in data:
            first_name_home, last_name_home = game[HOME_TEAM].split(" ")
            member_id_home = get_member_id(first_name_home, last_name_home)

            first_name_away, last_name_away = game[AWAY_TEAM].split(" ")
            member_id_away = get_member_id(first_name_away, last_name_away)
            db = get_db()
            query = db.execute(
                f"""
                SELECT * FROM game
                WHERE season=? AND week=?
                AND (team_A_id = ? AND team_B_id = ? OR team_A_id = ? AND team_B_id = ?)                
                """, (year, game[WEEK], member_id_home, member_id_away, member_id_away, member_id_home)
            ).fetchone()
            if query:
                if query[TEAM_A_SCORE] == game["home_score"] and query[TEAM_B_SCORE] == game["away_score"]:
                    continue
                else:
                    if write:
                        db.execute(
                            f"""
                            UPDATE game
                            SET 
                            {TEAM_A_SCORE}=?, 
                            {TEAM_B_SCORE}=?
                            WHERE
                            {GAME_ID}=?
                            """, (game["home_score"], game["away_score"], query[GAME_ID])
                        )
                        db.commit()

                    game["home_team_id"] = member_id_home
                    game["away_team_id"] = member_id_away
                    updates.append(game)
            else:
                if write:
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

                game["home_team_id"] = member_id_home
                game["away_team_id"] = member_id_away
                new_additions.append(game)

            close_db()

    columns = ["Season", "Week", "Team A Name",
               "Team A Score", "Team B Name", "Team B Score"]
    updated_df = pd.DataFrame(columns=columns)
    updated_html = None

    additions_df = pd.DataFrame(columns=columns)
    additions_html = None

    if data:
        for row in updates:
            updated_df.loc[len(updated_df.index)] = [
                row[SEASON],
                row[WEEK],
                row["home_team"],
                row["home_score"],
                row["away_team"],
                row["away_score"]
            ]
        updated_html = updated_df.to_html(classes="table table-striped")

        for row in new_additions:
            additions_df.loc[len(additions_df)] = [
                row[SEASON],
                row[WEEK],
                row["home_team"],
                row["home_score"],
                row["away_team"],
                row["away_score"]
            ]
        additions_html = additions_df.to_html(classes="table table-striped")

    close_db()
    return render_template("fetch_games_results.html",
                           year=year,
                           write=write,
                           updates=updated_html,
                           additions=additions_html,
                           num_changes=len(updates) + len(new_additions), title="Data Available")
