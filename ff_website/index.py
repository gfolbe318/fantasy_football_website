from flask import render_template, request, url_for
from ff_website.db import get_db
from ff_website import app


@app.route("/", methods=["GET", "POST"])
def hello():
    conn = get_db()
    conn.execute("""
        INSERT INTO members 
        (firstname, lastname, year_joined, active)
        VALUES (?, ?, ?, ?)""",
                 ("Garrett", "Folbe", 2016, 1)
                 )
    conn.commit()
    return "Hello world!"


@app.route("/test", methods=["GET", "POST"])
def test():
    conn = get_db()
    conn.execute("DELETE FROM members WHERE firstname = ?", ("Garrett",))
    conn.commit()
    conn.close()
    return "Hello world"
