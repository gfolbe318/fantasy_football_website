from flask import render_template, request, url_for
from ff_website.db import get_db
from ff_website import app


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


@app.route("/test", methods=["GET", "POST"])
def test():
    return "Hello world"
