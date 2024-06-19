import os
import random
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session, flash
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

        # NOTE: this does not work .. need to figure out how to build better, more complete solution
        # flash("Login successful, generating recommendations ... ")

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
        one_removed.append(related_artists["artists"][random.randint(4, 8)]["id"])

    # now, for each once-removed artist, want to get twice-removed artists through "related artist" call
    for artist_id in one_removed:
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        two_removed.append(related_artists["artists"][random.randint(4, 8)]["id"])

    # then, for each twice-removed artist, want to get five three-time-removed artists
    for artist_id in two_removed:
        subset = []
        indices = random.sample(range(4, 14), 5)
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        # TODO: change from "name" to "id"
        subset.append(related_artists["artists"][indices[0]]["id"])
        subset.append(related_artists["artists"][indices[1]]["id"])
        subset.append(related_artists["artists"][indices[2]]["id"])
        subset.append(related_artists["artists"][indices[3]]["id"])
        subset.append(related_artists["artists"][indices[4]]["id"])
        three_removed.append(subset)

    print(three_removed)

    # let's just create a dict and then return the whole dict?
    recs_dict = {}

    # for each group of recommendations
    for rec_group in three_removed:
        # go through each specific id
        for rec_id in rec_group:
            # get the top tracks for that ID
            response = requests.get(API_BASE_URL + 'artists/' + rec_id + '/top-tracks', headers=headers)
            top_tracks = response.json()
            # iterate through tracks until reach one that comes from album ... 
            for track in top_tracks["tracks"]:
                    if track['album']['album_type'] == "album": 
                        # add to overall dictionary
                        recs_dict[rec_id] = track['album']["name"]
                        # NOTE: only want to add the first one, then no more ...
                        break

    # print that overall dict
    # currently, key value pair between artist id and album name
    print(recs_dict)

    # NOTE: going to have to convert the ids back into names .. also going to have to display on the website somehow 

    '''
    so, at this point, three_removed is a list of 5 lists, that all contain the ids of 5 artitsts. 
    so now, for each id within each list, going to want to get the top tracks. 
    then, once i have the top tracks, want to traverse the list until I get to an album
    then, return that album (but make sure that it is still associated with the artitst)
    NOTE: what if an artist doesn't have any albums? What do we do at that point?

    '''

    return(jsonify(top_tracks))


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