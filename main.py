import os
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY')

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET =os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

AUTH_URL = os.getenv('AUTH_URL')
TOKEN_URL = os.getenv('TOKEN_URL')
API_BASE_URL = os.getenv('API_BASE_URL')

'''
Given albums (json) and dictionary of album/artist names, add the new albums/artists to dict.
Return the number of albums that were added.
'''
def add_albums(albums, album_dict):
    album_count = 0

    for item in albums["items"]:
        item_artists = []
        for artist in item['album']['artists']:
            item_artists.append(artist['name'])
        album_dict[item["album"]["name"]] = item_artists
        album_count += 1

    return album_count
 
@app.route('/')
def index():
    '''
    welcome page, redirect to login.
    '''
    return "Welcome to RecordRecs <a href='/login'>Login with Spotify</a>"
    
@app.route('/login')
def login():
    '''
    login with Spotify account.
    '''

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

    return redirect(auth_url)

@app.route("/callback")
def callback():
    '''
    once user has successfully logged in.
    '''

    # check for error
    if "error" in request.args: 
        return jsonify({"error" : request.args['error']})
    
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

        session['access_token'] = token_info['access_token']
        session["refresh_token"] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        # number of seconds from epoch + time until expiration 
        # this is necessary because we have to check if the access_token has expired

        return redirect('/saved-albums')
    
@app.route('/saved-albums')
def get_saved_albums():
    '''
    get all albums saved by user
    '''

    # if access token does not exist
    if 'access_token' not in session:
        return redirect("/login")
    
    # if access token has expired
    if datetime.now().timestamp() > session['expires_at']:
        # TODO: write this endpoint
        return redirect("/refresh-token")

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + 'me/albums?limit=50&offset=0', headers=headers)
    albums = response.json()

    '''
    dict. to streo album/artist names.
    key: album name
    value: list of artist(s)s
    '''
    saved_albums = {}

    num_added_albums = add_albums(albums, saved_albums)

    '''
    NOTE: per Spotify documentation, cannot get more than 50 saved albums at one time.
    Thus, need to iterate over calls if user has more than 50 saved albums.
    '''
    if num_added_albums == 50:
        # have to change offset as get more results
        repetitions = 1
        # as long as we are getting 50 albums in each response, want to make another call
        while num_added_albums == 50:
            response = requests.get(API_BASE_URL + 'me/albums?limit=50&offset=' + str(num_added_albums * repetitions), headers=headers)
            albums = response.json()
            num_added_albums = add_albums(albums, saved_albums)
            repetitions += 1

    # OK, at this point we are able to get all the albums that a user has saved to their library ..
    # the next steps are going to be to get the artists? not really sure what to do from here tbh. 

    print(saved_albums)
    return(jsonify(albums))


# TODO: have to actually write this endpoint TBH
@app.route('/refresh-token')
def refresh_token():
    ''' 
    refresh token if access token has expired 
    '''
    # if refresh token does not exist
    if "refresh_token" not in session:
        return redirect("/login")
    
    print("WE ARE REFRESHING")
    # NOTE: not going to write the logic because I am going to change this anyways

    return redirect("/saved-albums")

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True) 
