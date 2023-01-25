import os
import pathlib

import requests
from flask import Flask, Blueprint, session, abort, redirect, request, make_response
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
import psycopg2
from app import db 
from app.models.profile import Profile

app_bp = Blueprint("app", __name__)
#profiles_bp = Blueprint("app", __name__, url_prefix="/profiles")

load_dotenv()


app = Flask("Google Login App")
app.secret_key = os.environ.get("CLIENT_SECRET") # make sure this matches with that's in client_secret.json

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = os.environ.get("CLIENT_ID")
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@app_bp.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app_bp.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )



    session["google_id"] = str(id_info.get("sub"))
    session["name"] = id_info.get("name")
    if session["google_id"]:
        authenticate_subs()
    return redirect("/profiles/profile_id")


############ ROUTES FOR GOOGLE AUTH ###############
###################################################

@app_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app_bp.route("/", methods=["GET"])
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app_bp.route("/profiles/profile_id")
@login_is_required
def profile_id_redirect():
    conn = None
    sub_id = session["google_id"]
    try:
        conn = psycopg2.connect(database = "travel_tracker_development", user = "postgres", password = "postgres", host = "127.0.0.1", port = "5432")
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM profile WHERE sub = '{sub_id}'")
        profile_id = cur.fetchone()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return f"{profile_id}"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
    



# helper function
def validate_model(cls, model_id):
    try: 
        model_id = int(model_id)
    except:
        abort(make_response({"message": f"{cls.__name__} {model_id} invalid"}, 400)) 

    model = cls.query.get(model_id)
    
    if not model:
        abort(make_response({"message": f"{cls.__name__} {model_id} not found"}, 404)) 

    return model



########### ROUTES TO CREATE PROFILE ###############
####################################################


def authenticate_subs():
    # creating variable conn, start as None- if its not none it will close database
    # if database is left open could cause issues
    conn = None
    sub_id = session["google_id"]
    try:
        # connects to database 
        conn = psycopg2.connect(database = "travel_tracker_development", user = "postgres", password = "postgres", host = "127.0.0.1", port = "5432")
        # object to execute query, how psycopg2 library works
        cur = conn.cursor()
        # executing SQL query
        cur.execute(f"SELECT sub FROM profile WHERE sub = '{sub_id}'")
        # fetching row of data from the query 
        row = cur.fetchone()
        if row == None:
            # create new profile in database
            # add user info (sub, name) from google auth
            new_profile = Profile(
                sub=sub_id,
                name=session["name"],
            )
            
            db.session.add(new_profile)
            db.session.commit()
        
        # close the cursor
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    # close the database so connection is not left open
    finally:
        if conn is not None:
            conn.close()
