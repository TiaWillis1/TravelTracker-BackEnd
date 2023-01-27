import os
import pathlib

import requests
from flask import Flask, Blueprint, session, abort, jsonify, redirect, request, make_response
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
import psycopg2
from app import db 
from app.models.profile import Profile
from app.models.pin import Pin

app_bp = Blueprint("app", __name__)
#pins_bp = Blueprint("app", __name__, url_prefix="/pins")

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
    name = session["name"]
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
    return f"Welcome {name} your profile number is {profile_id}"


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=80, debug=True)
    



# helper function
def validate_model(cls, model_id):
    try: 
        model_id = int(model_id)
    except:
        abort(make_response({"message from validate model": f"{cls.__name__} {model_id} invalid"}, 400)) 

    model = cls.query.get(model_id)
    
    if not model:
        abort(make_response({"message": f"{cls.__name__} {model_id} not found"}, 404)) 

    return model



########### ROUTES/FUNCTIONS FOR PROFILE ###############
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

@app_bp.route("/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    profile = validate_model(Profile,profile_id)

    db.session.delete(profile)
    db.session.commit()
    deleted_profile_dict = {"details":f"Profile {profile.id} successfully deleted"}

    return make_response(jsonify(deleted_profile_dict), 200)



def get_lat_long(address): 


    params = {'key': os.environ.get("G_KEY"),
    'address' : address}

    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    response = requests.get(base_url, params=params)
    data = response.json() 
    if data['status'] == 'OK':
        result = data['results'][0]
        location = result['geometry']['location']
        geo_coord_list = [location['lat'], location['lng']]
        return geo_coord_list
    else:
        return f"Address invalid, please check your request and try again"



@app_bp.route("/profiles/<profile_id>/pins", methods=["POST"])
def create_pin(profile_id):
    request_body = request.get_json()
    get_geocode_coord = get_lat_long(request_body["location_name"])
    print(get_geocode_coord[0])
    print(get_geocode_coord[1])

    profile = validate_model(Profile, profile_id)

    try:
        new_pin = Pin(
            longitude = get_geocode_coord[1],
            latitude = get_geocode_coord[0],
            location_name = request_body["location_name"],
            date = request_body["date"]
        )
    except KeyError:
        return make_response({"details make response": "Invalid data"}, 400)

    conn = None
    try:
        conn = psycopg2.connect(database = "travel_tracker_development", user = "postgres", password = "postgres", host = "127.0.0.1", port = "5432")
        cur = conn.cursor()
        cur.execute(f"SELECT location_name FROM pin WHERE profile_id = '{profile_id}' INTERSECT SELECT location_name FROM pin WHERE location_name = '{new_pin.location_name}'")
        locations = cur.fetchone()
        if locations == None:
            db.session.add(new_pin)
            db.session.commit()
            profile.pins.append(new_pin)
            db.session.add(profile)
            db.session.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
        if new_pin.id == None:
            return f"pin already exists, no duplicate pins allowed"   
        else:
            return make_response(new_pin.to_dict_pins(), 201)


# route to delete a pin 
@app_bp.route("/pins/<pin_id>", methods=["DELETE"])
def delete_pin(pin_id):
    pin = validate_model(Pin,pin_id)

    db.session.delete(pin)
    db.session.commit()
    deleted_pin_dict = {"details":f"Pin for {pin.location_name} successfully deleted"}

    return make_response(jsonify(deleted_pin_dict), 200)


        

