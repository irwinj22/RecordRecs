import os
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session
from dotenv import load_dotenv

'''
NOTE: this is a really simple version, just trying to get set up with Flask and what not.
What I will be building will be a lot more complicated.
'''

app = Flask(__name__)
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY')

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET =os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

AUTH_URL = os.getenv('AUTH_URL')
TOKEN_URL = os.getenv('TOKEN_URL')
API_BASE_URL = os.getenv('API_BASE_URL')

# show them a welcome page, redirect to login page. 
@app.route('/')
def index():
    return "Welcome to RecordRecs <a href='/login'>Login with Spotify</a>"
    
# Login endpoint
@app.route('/login')
def login():
    scope = "user-read-private user-read-email"

    params = {
        'client_id' : CLIENT_ID,
        'response_type' : 'code',
        'scope' : scope,
        'redirect_uri' : REDIRECT_URI,
        # set true to test locally --> user has to log in every time
        'show_dialog' : True 
    }

    # TODO: change this so readable
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

# Where we are going to go if user logs in successfully
@app.route("/callback")
def callback():
    # check for error
    if "error" in request.args: 
        return jsonify({"error" : request.args['error']})
    
    if 'code' in request.args: 
        req_body = {
            'code' : request.args['code'], 
            'grant_type' : 'authorization_code',
            'redirect_uri' : REDIRECT_URI,
            'client_id' : CLIENT_ID, 
            'client_secret' : CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        # get the response back, will contain some info
        token_info = response.json()

        # this is what is important (3 pieces of info)
        session['acccess_token'] = token_info['access_token']
        session["refresh_token"] = token_info['refresh_token']
        # number of seconds from epoch + time until expiration 
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        # this is necessary because we have to check if the access_token has expired

        return redirect('/playlists')
    
@app.route('/playlists')
def get_playlists():
    # if access token does not exist
    if 'access_token' not in session:
        return redirect("/login")
    
    # if access token has expired
    if datetime.now().timestamp() > session['expires_at']:
        return redirect("/refresh-token")
        # TODO: write this endpoint

    # NOTE: not actualy going to make the request because I don't want the data. 
    print("YEAH BUDDY LET'S GET THOSE PLAYLISTS")

@app.route('/refresh-token')
def refresh_token():
    if "refresh_token" not in session:
        return redirect("/login")
    
    print("WE ARE REFRESHING")
    # NOTE: not going to write the logic because I am going to change this anyways

    return redirect("/playlists")

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True) 