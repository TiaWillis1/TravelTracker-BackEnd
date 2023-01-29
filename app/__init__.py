from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
#from flask_cors import CORS

db = SQLAlchemy()
# make sure type is updated when doing flask migrate
migrate = Migrate(compare_type=True)
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "SQLALCHEMY_DATABASE_URI")
    app.config["SECRET_KEY"] = os.environ.get("CLIENT_SECRET")


    db.init_app(app)
    migrate.init_app(app, db)

    # Import models here for Alembic setup
    from app.models.pin import Pin
    from app.models.profile import Profile


    # Register Blueprints here
    # from .routes import pins_bp
    # app.register_blueprint(pins_bp)

    # from .routes import profiles_bp
    # app.register_blueprint(profiles_bp)

    from .routes import app_bp
    app.register_blueprint(app_bp)
    

    #CORS(app)
    return app
