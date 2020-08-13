from flask import Flask, render_template
from forms import createOwner
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'


@app.route('/', methods=["GET", "POST"])
def hello_world():
    return render_template("home.html", form=createOwner())
