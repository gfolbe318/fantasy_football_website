from flask import render_template, request, url_for
from ff_website.db import get_db
from ff_website import app


@app.route("/", methods=["GET", "POST"])
def hello():
    return "Hello world!"


@app.route("/test", methods=["GET", "POST"])
def test():
    return "Hello world"
