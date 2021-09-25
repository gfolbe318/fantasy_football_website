import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from ff_website import credentials

from . import db

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=credentials.xss_key,
    DATABASE=os.path.join(app.instance_path, "logs.sqlite"),
)

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db.init_app(app)
csrf = CSRFProtect(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


from ff_website import index
from ff_website import apis