from ff_website.db import get_db, init_db
from ff_website import app
from ff_website.constants import *

"""
These are helper functions that are only used in a controlled context, such as uploading 
data en masse. Do not use for any other context.
"""


def get_all_members():
    """
    Returns a list of all members that are queried from the database
    """
    with app.app_context():
        init_db()
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


def get_member_id(first_name, last_name):
    """
    Returns the member_id of a league member given their first and last name
    """
    with app.app_context():
        init_db()
        db = get_db()
        member_id = db.execute(
            f"""
            SELECT {MEMBER_ID} FROM member
            WHERE {FIRST_NAME}=? AND {LAST_NAME}=?
            """,
            (first_name, last_name)
        ).fetchall()

        db.close()

        return member_id[0][MEMBER_ID]
