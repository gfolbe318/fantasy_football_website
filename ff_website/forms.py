from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.fields.simple import PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError, Email, EqualTo

import email_validator

from ff_website.constants import CURRENT_SEASON


def get_all_members_helper():

    x = [("", "Please select a member...")]
    x.extend([(i, f"Loading Player Name...") for i in range(20)])

    return x


def get_years_helper(start, stop):

    placeholder = [("", "Select a year...")]
    years = placeholder + [(x, x) for x in range(start, stop+1)]
    return years


def get_weeks(include_zero=False):
    if include_zero:
        start = 0
    else:
        start = 1
    return [("", "Select a week...")] + [(x, x) for x in range(start, 18)]


class HeadToHead(FlaskForm):

    members = get_all_members_helper()

    def valid_names_one(self, leagueMemberOne):
        if self.leagueMemberTwo.data == leagueMemberOne.data and leagueMemberOne.data:
            raise ValidationError("League members must be different")

    def valid_names_two(self, leagueMemberTwo):
        if self.leagueMemberOne.data == leagueMemberTwo.data and leagueMemberTwo.data:
            raise ValidationError("League members must be different")

    leagueMemberOne = SelectField(
        "League Member One", choices=members, validators=[DataRequired("Please select a league member"), valid_names_one], coerce=str)
    leagueMemberTwo = SelectField(
        "League Member Two", choices=members, validators=[DataRequired("Please select a league member"), valid_names_two])

    submit = SubmitField("Compare members")


class GameQualities(FlaskForm):

    filter = SelectField('Filter',
                         choices=[
                             ("", "Select a filter..."),
                             (1, "Fewest Points Scored (Combined)"),
                             (2, "Fewest Points Scored (Individual)"),
                             (3, "Most Points Scored (Combined)"),
                             (4, "Most Points Scored (Individual)"),
                             (5, "Largest Margin of Victory"),
                             (6, "Smallest Margin of Victory")],
                         validators=[DataRequired("Please select a filter")])

    numberOfResults = SelectField('Number of Results',
                                  choices=[(10, 10),
                                           (25, 25),
                                           (100, 100)])

    submit = SubmitField("Get Results")


class SeasonSelector(FlaskForm):

    year = SelectField('Season',
                       choices=[("", "Please select a season..."),
                                ("2017", "2017"), ("2018", "2018"),
                                ("2019", "2019"), ("2020", "2020"),
                                ("2021", "2021"), ("2022", "2022"),
                                ("2023", "2023")],
                       validators=[DataRequired("Please select a season")])

    submit = SubmitField("View Season")


class CreateMember(FlaskForm):
    years = get_years_helper(2011, CURRENT_SEASON)

    initialYear = SelectField(
        "Year Joined", choices=years, validators=[DataRequired()])
    firstName = StringField("First Name", validators=[DataRequired()])
    lastName = StringField("Last Name", validators=[DataRequired()])
    image = FileField("Avatar")
    activeMember = SelectField("Activity Status...",
                               choices=[("", "Select a status"),
                                        (1, "Active"),
                                        (0, "Inactive")],
                               validators=[DataRequired()]
                               )

    submit = SubmitField("Submit")


class CreateGame(FlaskForm):

    def valid_names_one(self, teamA):
        if self.teamBName.data == teamA.data:
            raise ValidationError("League members must be different")

    def valid_names_two(self, teamB):
        if self.teamAName.data == teamB.data:
            raise ValidationError("League members must be different")

    members = get_all_members_helper()

    teamAScore = FloatField("Team A Score", validators=[DataRequired()])
    teamAName = SelectField(
        "Team A Name", choices=members, validators=[DataRequired(), valid_names_one])

    teamBScore = FloatField("Team B Score", validators=[DataRequired()])
    teamBName = SelectField(
        "Team B Name", choices=members, validators=[DataRequired(), valid_names_two])

    years = get_years_helper(2017, CURRENT_SEASON)
    season = SelectField("Season", choices=years,
                         validators=[DataRequired()])

    weeks = get_weeks()
    week = SelectField("Week", choices=weeks, validators=[DataRequired()])

    matchupLength = SelectField("Matchup Length",
                                choices=[("", "Select a length..."),
                                         (1, 1),
                                         (2, 2)],
                                validators=[DataRequired()])

    playoffs = SelectField("Matchup Format",
                           choices=[("", "Select a Matchup Format..."),
                                    (0, "Regular Season"), (1, "Post Season")],
                           validators=[DataRequired()])

    submit = SubmitField("Submit")


class CreatePowerRankings(FlaskForm):
    members = get_all_members_helper()
    weeks = get_weeks(True)

    week = SelectField("Week", choices=weeks, validators=[DataRequired()])

    team_one = SelectField(
        "#1", choices=members, validators=[DataRequired()])
    team_two = SelectField(
        "#2", choices=members, validators=[DataRequired()])
    team_three = SelectField(
        "#3", choices=members, validators=[DataRequired()])
    team_four = SelectField(
        "#4", choices=members, validators=[DataRequired()])
    team_five = SelectField(
        "#5", choices=members, validators=[DataRequired()])
    team_six = SelectField(
        "#6", choices=members, validators=[DataRequired()])
    team_seven = SelectField(
        "#7", choices=members, validators=[DataRequired()])
    team_eight = SelectField(
        "#8", choices=members, validators=[DataRequired()])
    team_nine = SelectField(
        "#9", choices=members, validators=[DataRequired()])
    team_ten = SelectField(
        "#10", choices=members, validators=[DataRequired()])
    team_eleven = SelectField(
        "#11", choices=members, validators=[DataRequired()])
    team_twelve = SelectField(
        "#12", choices=members, validators=[DataRequired()])

    submit = SubmitField("Submit")


class SelectPowerRankWeek(FlaskForm):
    weeks = [("", "Select a week to view")] + \
        [(week, f"Week {week}") for week in range(1, 18)]
    week = SelectField("Select a week to view", choices=weeks,
                       validators=[DataRequired("Select a week to view")])
    submit = SubmitField("View")


class MakeAnnouncement(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    announcement = TextAreaField(
        'What do you want to say?', validators=[DataRequired()])
    submit = SubmitField("Create Announcement")


class JarrettReport(FlaskForm):
    weeks = get_weeks
    title = StringField('Title', validators=[DataRequired()])
    week = SelectField('Week', choices=get_weeks(include_zero=True),
                       validators=[DataRequired()])
    report = TextAreaField(
        'Report', validators=[DataRequired()])
    submit = SubmitField('Create Report')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(min=5, max=15, message="Username must be between 5 and 15 characters")])
    email = StringField('Email address',
                        validators=[DataRequired(), Email()])

    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('confirm_password', 'Passwords must match')])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),  EqualTo('password', 'Passwords must match')])
    submit = SubmitField()


class LoginForm(FlaskForm):
    username_or_email = StringField('Username/Email Address',
                                    validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField()


class changePassword(FlaskForm):
    current_password = PasswordField(
        'Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('confirm_password', 'New passwords do not match')])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('new_password', 'New passwords do not match')])

    submit = SubmitField('Update Password')
