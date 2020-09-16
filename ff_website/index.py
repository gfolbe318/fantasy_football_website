from flask import render_template, request, url_for
from ff_website.db import get_db
from ff_website import app


@app.route("/", methods=["GET", "POST"])
def hello():
    photo = "static/img/gmf.jpg"
    l = [photo for _ in range(12)]
    return render_template("home.html", photos=l)


@app.route("/members", methods=["GET", "POST"])
def members():
        return render_template("members.html")


@app.route("/test", methods=["GET", "POST"])
def test():
    return "Hello world"
