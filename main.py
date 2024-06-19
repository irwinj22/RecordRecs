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
    albums = response.json()

    '''
    dict. to streo album/artist names.
    key: album name
    value: list of artist(s)s
    '''
    recent_artists = []

    # add the first artist from each of the 5 most "recent" albums
    for item in albums["items"]:
        recent_artists.append(item['album']['artists'][0]['id'])

    # now, for each artist, want to get the similair artists, or something like that

    print(recent_artists)

    
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

'''
maybe just need to get the artits that have been listened to, since I am not going
to be cross-referencing with the albums anyways

so yeah, i can just loop through and get the artits, then get get similar artits multiple times
for each of those artists
then, once i have the final artits, i can just get the albums, put them together with the artists, 
and then diplay them in some way that makes a lot of sense and what not. 
'''


'''
a whole list of TODO
re-organize so that the endpoints are in different files
get this working on a real server (Render)
make the pages look a little better? -- see Flask manual
go through the artist route so that we can have good recs
NOTE: i am actually going to want to get the artist IDs, not the names of the artists
how can I speed up this program? Do I really need to grab every saved album? 
'''

# ALSO, the sight is super slow, and this is without even making the other calls .. how can I speed this whole
# thing up ... also i am only going to want to look at all the albums once, i am not going to want to do that 
# again tbh. 

# TODO: add a note on how spotify defines "recent"