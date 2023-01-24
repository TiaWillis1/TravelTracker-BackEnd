import os
import pathlib

import requests
from flask import Flask, Blueprint, session, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv


app_bp = Blueprint("app", __name__)
profiles_bp = Blueprint("app", __name__, url_prefix="/profiles")

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



    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/protected_area")


############ ROUTES FOR GOOGLE AUTH ###############
###################################################

@app_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app_bp.route("/", methods=["GET"])
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app_bp.route("/protected_area")
@login_is_required
def protected_area():
    #return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"
    return f"{session['google_id']}"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)



########### ROUTES TO CREATE PROFILE ###############
####################################################


#CREATE PROFILE ROUTE 

# @profiles_bp.route("", methods=["POST"]) 
# def create_profile():

#     if session['google_id'] not in travel_tracker_development: 

