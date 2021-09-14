from datetime import datetime

from flask_wtf import FlaskForm
from flask_wtf.file import FileField,  FileRequired
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.fields.core import BooleanField, FloatField
from wtforms.validators import DataRequired, ValidationError

from ff_website.apis import get_all_members
from ff_website.constants import FIRST_NAME, LAST_NAME, MEMBER_ID


def get_all_members_helper():

    placeholder = [("", "Please select a member...")]

    all_members = get_all_members()
    members = placeholder + [
        (f"{member[MEMBER_ID]}",
         f"{member[FIRST_NAME]} {member[LAST_NAME]}") for member in all_members
    ]

    return members


def get_years_helper(start):

    placeholder = [("", "Select a year...")]

    current_year = datetime.now().year
    years = placeholder + [(x, x) for x in range(start, current_year + 1)]
    return years


def get_weeks():
    return [("", "Select a week...")] + [(x, x) for x in range(1, 15)] + [("PS", "PostSeason")]


class HeadToHead(FlaskForm):

    members = get_all_members_helper()

    def valid_names_one(self, leagueMemberOne):
        if self.leagueMemberTwo.data == leagueMemberOne.data and leagueMemberOne.data:
            raise ValidationError("League members must be different")

    def valid_names_two(self, leagueMemberTwo):
        if self.leagueMemberOne.data == leagueMemberTwo.data and leagueMemberTwo.data:
            raise ValidationError("League members must be different")

    leagueMemberOne = SelectField(
        "League Member One", choices=members, validators=[DataRequired(), valid_names_one])
    leagueMemberTwo = SelectField(
        "League Member Two", choices=members, validators=[DataRequired(), valid_names_two])

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
                                ("2019", "2019"), ("2020", "2020")],
                       validators=[DataRequired()])

    submit = SubmitField("View Season")


class CreateMember(FlaskForm):
    years = get_years_helper(2011)

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

    def validate_week(self, postSeason):
        if (self.week.data == "PS" and postSeason.data == "0") or \
                (self.week.data != "PS" and postSeason.data == "1"):
            raise ValidationError("Mismatch in week")

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

    years = get_years_helper(2017)
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
                           validators=[DataRequired(), validate_week])

    submit = SubmitField("Submit")
