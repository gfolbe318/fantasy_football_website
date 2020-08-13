from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired


class createOwner(FlaskForm):
    years = [(x, x) for x in range(2011, 2020)]

    firstName = StringField("First Name", validators=[DataRequired()])
    lastName = StringField("Last Name", validators=[DataRequired()])
    yearJoined = SelectField(
        "Year Joined", choices=years, validators=[DataRequired()])
    submit = SubmitField("Submit")
