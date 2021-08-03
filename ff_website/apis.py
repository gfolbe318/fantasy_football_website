from ff_website.db import get_db
from ff_website import app
from ff_website.constants import *


def get_all_members():
    """
    Returns a list of all members that are queried from the database
    """
    with app.app_context():
        db = get_db()
        all_members = db.execute(
            f"""
            SELECT {MEMBER_ID}, {FIRST_NAME}, {LAST_NAME}, {YEAR_JOINED}, {ACTIVE}  FROM member
            """
        ).fetchall()

        return [
            {
                MEMBER_ID: i[0],
                FIRST_NAME: i[1],
                LAST_NAME: i[2],
                YEAR_JOINED: i[3],
                ACTIVE: i[4]
            } for i in all_members
        ]