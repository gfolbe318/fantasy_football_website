DROP TABLE IF EXISTS member;
DROP TABLE IF EXISTS game;

CREATE TABLE member
(
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    year_joined INTEGER NOT NULL,
    active INTEGER NOT NULL
);


CREATE TABLE game
(
    game_id INTEGER PRIMARY KEY,
    team_A_score FLOAT NOT NULL,
    team_B_score FLOAT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    matchup_length INTEGER NOT NULL,
    playoffs INTEGER NOT NULL,
    team_A_id INTEGER NOT NULL,
    team_B_id INTEGER NOT NULL,
    FOREIGN KEY (team_A_id) REFERENCES member (member_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (team_B_id) REFERENCES member (member_id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- https://stackoverflow.com/questions/25675314/how-to-backup-sqlite-database