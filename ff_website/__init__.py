from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
from ff_website import credentials


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=credentials.xss_key,        
        DATABASE=os.path.join(app.instance_path, "logs.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)
    csrf = CSRFProtect(app)
    return app


app = create_app()
import ff_website.index