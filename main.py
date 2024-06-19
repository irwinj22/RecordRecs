import os
import random
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
Given albums (json) and dictionary of album/artist ids, add the new albums/artists to dict.
Return the number of albums that were added.
'''
def add_albums(albums, album_dict):
    album_count = 0

    for item in albums["items"]:
        item_artists = []
        for artist in item['album']['artists']:
            item_artists.append(artist['id'])
        album_dict[item["album"]["id"]] = item_artists
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

    # NOTE: only want to get 5 most recently-added projects and what not
    response = requests.get(API_BASE_URL + 'me/albums?limit=5&offset=0', headers=headers)
    recent_albums = response.json()

    # bunch of lists that I am going to use to store all sorts of info in
    recent_artists = []
    one_removed = []
    two_removed = []
    three_removed = []

    # add the first artist from each of the 5 most "recent" albums
    for item in recent_albums["items"]:
        recent_artists.append(item['album']['artists'][0]['id'])

    # TODO: lots of duplication that can be removed

    # now, for each recent artist, want to get once-removed artists through "related artist" call
    for artist_id in recent_artists:
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        one_removed.append(related_artists["artists"][random.randint(4, 14)]["id"])

    # now, for each once-removed artist, want to get twice-removed artists through "related artist" call
    for artist_id in one_removed:
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        two_removed.append(related_artists["artists"][random.randint(4, 14)]["id"])

    # then, for each twice-removed artist, want to get five thrice-removed artists
    for artist_id in two_removed:
        subset = []
        indices = random.sample(range(4, 14), 5)
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        # TODO: change from "name" to "id"
        subset.append(related_artists["artists"][indices[0]]["name"])
        subset.append(related_artists["artists"][indices[1]]["name"])
        subset.append(related_artists["artists"][indices[2]]["name"])
        subset.append(related_artists["artists"][indices[3]]["name"])
        subset.append(related_artists["artists"][indices[4]]["name"])
        three_removed.append(subset)
        
    print(three_removed)
    # now, want to get ONE of fourth-eighth related artists
    return(jsonify(recent_albums))


# TODO: have to actually write this endpoint
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

'''
a whole list of TODO
re-organize so that the endpoints are in different files
get this working on a real server (Render)
make the pages look a little better? -- see Flask manual
go through the artist route so that we can have good recs
NOTE: i am actually going to want to get the artist IDs, not the names of the artists
how can I speed up this program? Do I really need to grab every saved album? 
'''

# TODO: add a note on how spotify defines "recent" for the albums