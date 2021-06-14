from flask import render_template, request, url_for, jsonify
from ff_website.db import get_db
from ff_website import app
from forms import GameQualities, HeadToHead


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


@app.route("/apis/all_members", methods=["GET"])
def get_members():
    """
    SELECT member_id, first_name, last_name FROM members....
    """

    return jsonify(
        [
            {"member_id": 1,
             "name": "Garrett Folbe"},
            {"member_id": 2,
             "name": "Noah Nathan"},
            {"member_id": 3,
             "name": "Merrick Weingarten"}
        ]
    )
