import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
import datetime
import json


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()
    click.echo("Initialized databases")


def get_member_name(id):
    """
    Return the member_name given the ID of the member
    """

    init_db()
    db = get_db()
    member = db.execute(
        f"""
        SELECT first_name, last_name from member
        WHERE member_id=?
        """, (id,)
    ).fetchall()

    first_name = member[0]["first_name"]
    last_name = member[0]["last_name"]
    return f"{first_name} {last_name}"


@click.command("backup-db")
@with_appcontext
def backup_db_command():
    db = get_db()
    member_query = db.execute(
        """
        SELECT * FROM member
        """
    ).fetchall()
    member_data = [{
        "member_id": i["member_id"],
        "first_name": i["first_name"],
        "last_name": i["last_name"],
        "year_joined": i["year_joined"],
        "active": i["active"],
        "img_filepath": i["img_filepath"]
    } for i in member_query]

    game_query = db.execute(
        """
        SELECT * FROM game
        """
    ).fetchall()

    game_data = [{
        "season": i["season"],
        "week": i["week"],
        "matchup_length": i["matchup_length"],
        "playoffs": bool(i["playoffs"]),
        "home_team": get_member_name(i["team_A_id"]),
        "home_score": i["team_A_score"],
        "away_team": get_member_name(i["team_B_id"]),
        "away_score": i["team_B_score"]
    } for i in game_query]

    ct = datetime.datetime.now()
    year = ct.year
    month = ct.month
    day = ct.day

    members_filename = f"ff_website/data/backups/members-{year}-{month}-{day}.json"
    games_filename = f"ff_website/data/backups/games-{year}-{month}-{day}.json"

    json.dump(member_data, open(members_filename, "w"), indent=4)
    json.dump(game_data, open(games_filename, "w"), indent=4)


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(backup_db_command)
