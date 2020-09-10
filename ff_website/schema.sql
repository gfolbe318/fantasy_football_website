DROP TABLE IF EXISTS members;

CREATE TABLE members
(
    id INTEGER PRIMARY KEY,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    year_joined INTEGER,
    active INTEGER
);