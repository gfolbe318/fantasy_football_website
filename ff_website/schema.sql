CREATE TABLE IF NOT EXISTS member
(
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    year_joined INTEGER NOT NULL,
    active INTEGER NOT NULL,
    img_filepath TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS game
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


CREATE TABLE IF NOT EXISTS user
(
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    admin_privileges INTEGER NOT NULL,
    announcement_privileges INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS announcement
(
    announcement_id INTEGER PRIMARY KEY,
    author TEXT NOT NULL,
    title TEXT NOT NULL,
    announcement TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (author) REFERENCES user (user_id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report
(
    report_id INTEGER PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    title TEXT NOT NULL,
    static_url TEXT NOT NULL
)