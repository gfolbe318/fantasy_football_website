from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms import validators
from wtforms.validators import DataRequired, ValidationError


class createOwner(FlaskForm):
    years = [(x, x) for x in range(2011, 2020)]

    firstName = StringField("First Name", validators=[DataRequired()])
    lastName = StringField("Last Name", validators=[DataRequired()])
    initialYear = SelectField(
        "Year Joined", choices=years, validators=[DataRequired()])
    submit = SubmitField("Submit")


class HeadToHead(FlaskForm):

    members = [("", "Please select a league member..."), (1, "Garrett Folbe"),
               (2, "Noah Nathan"), (3, "Jason Silverstone")]

    def valid_names_one(self, leagueMemberOne):
        if self.leagueMemberTwo.data == leagueMemberOne.data:
            raise ValidationError("League members must be different")

    def valid_names_two(self, leagueMemberTwo):
        if self.leagueMemberOne.data == leagueMemberTwo.data:
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
                             (4, "Most Points Scored (Individual"),
                             (5, "Largest Margin of Victory"),
                             (6, "Smallest Margin of Victory")],
                         validators=[DataRequired("Please select a filter")])

    numberOfResults = SelectField('Number of Results',
                                  choices=[(10, 10),
                                           (25, 25),
                                           (100, 100)])
    submit = SubmitField("Get Results")
