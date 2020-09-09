from flask import Flask, render_template, g, current_app
from flask.cli import with_appcontext


from forms import createOwner
import sqlite3


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'


@app.route('/', methods=["GET", "POST"])
def hello_world():
    return render_template("home.html", form=createOwner())
