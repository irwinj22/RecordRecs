import os
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Blueprint, flash, g, redirect, render_template, request, jsonify, session, url_for
)

bp = Blueprint("auth", __name__, url_prefix="/auth")

# load environment variables
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET =os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
REDIRECT_URI = "https://irwinj22.pythonanywhere.com/auth/callback"
AUTH_URL = os.getenv('AUTH_URL')
TOKEN_URL = os.getenv('TOKEN_URL')
API_BASE_URL = os.getenv('API_BASE_URL')

'''
Login with Spotify account.
'''
@bp.route('/login')
def login():
    # print("HI")
    # print("REDIRECT_URI: ", REDIRECT_URI)
    # what we need access to
    scope = "user-read-private user-read-email user-library-read"
    params = {
        'client_id' : CLIENT_ID,
        'response_type' : 'code',
        'scope' : scope,
        'redirect_uri' : REDIRECT_URI,
        # set true to test locally --> user has to log in every time
        'show_dialog' : True 
    }

    # TODO: change? 
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print("auth_url: ", auth_url)

    return redirect(auth_url)

'''
User successfully logs in, get session info.
'''
@bp.route('/callback')
def callback():
    print("WE HAVE MADE IT TO THE CALLBACK")
    # error occurs iff "cancel" pressed during login process, 
    # so will just redirect to homepage.
    if "error" in request.args: 
        return redirect(url_for("index.index"))

    # if we get good response
    if 'code' in request.args: 
        req_body = {
            'code' : request.args['code'], 
            'grant_type' : 'authorization_code',
            'redirect_uri' : REDIRECT_URI,
            'client_id' : CLIENT_ID, 
            'client_secret' : CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        print("TOKEN_INFO: ", token_info)

        session['access_token'] = token_info['access_token']
        session["refresh_token"] = token_info['refresh_token']
        # number of seconds from epoch + time until expiration 
        # this is necessary because we have to check if the access_token has expired
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        # what if i just redirect to a different page, then from that page go and load the recs or something
        return render_template("rec/loading.html")
        # return redirect(url_for("rec.recs"))


# oh maybe my session has expired or something like that
