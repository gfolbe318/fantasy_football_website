from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError
from datetime import date


class createOwner(FlaskForm):
    years = [(x, x) for x in range(2011, 2020)]

    firstName = StringField("First Name", validators=[DataRequired()])
    lastName = StringField("Last Name", validators=[DataRequired()])
    initialYear = SelectField(
        "Year Joined", choices=years, validators=[DataRequired()])
    submit = SubmitField("Submit")


class H2H(FlaskForm):

    owners = [("", "Please select a league member..."), (1, "Garrett Folbe"),
              (2, "Noah Nathan"), (3, "Jason Silverstone")]

    def valid_names_one(self, leagueMemberOne):
        print("here")
        if self.leagueMemberTwo.data == leagueMemberOne.data:
            raise ValidationError("Cannot compare two of the same members")

    def valid_names_two(self, leagueMemberTwo):
        print("here")
        if self.leagueMemberOne.data == leagueMemberTwo.data:
            raise ValidationError("Cannot compare two of the same members")

    leagueMemberOne = SelectField(
        "League Member One", choices=owners, validators=[DataRequired(), valid_names_one])
    leagueMemberTwo = SelectField(
        "League Member Two", choices=owners, validators=[DataRequired(), valid_names_two])

    submit = SubmitField("Compare members")
