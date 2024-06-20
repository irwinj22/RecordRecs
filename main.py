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
 
'''
Welcome page, redirect to login.
'''
@app.route('/')
def index():
    return "Welcome to RecordRecs <a href='/login'>Login with Spotify</a>"
    
'''
Login with Spotify account.
'''
@app.route('/login')
def login():

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

    return redirect(auth_url)

'''
User successfully logs in, get session info.
'''
@app.route("/callback")
def callback():

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
        # number of seconds from epoch + time until expiration 
        # this is necessary because we have to check if the access_token has expired
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return redirect('/saved-albums')

'''
Get recently saved albums, make recommendations.
Recommendation logic: 
    1. For each recent album (last 5) in listener's library, get artist
    2. For each album artist, get a "related" artist (as defined by Spotify)
    3. For each related artist, get another related artist (now twice-removed)
    4. For each twice-removed artist, get 5 related arists (each of these will be three-times removed from original artist)
    5. Get a popular album for each of these five artists, totalling 25 albums (5 albums for each of 5 original albums in library)
    BOOM
'''
@app.route('/saved-albums')
def get_saved_albums():

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

    # NOTE: only want to get 5 most recently-added projects
    response = requests.get(API_BASE_URL + 'me/albums?limit=5&offset=0', headers=headers)
    recent_albums = response.json()

    recent_artists = []
    recent_projects = []
    one_removed = []
    two_removed = []
    three_removed = []

    # add the first artist from each of the 5 most "recent" albums
    for item in recent_albums["items"]:
        recent_artists.append(item['album']['artists'][0]['id'])
        recent_projects.append(tuple((item['album']['name'], item['album']['artists'][0]['name'])))

    # now, for each recent artist, want to get once-removed artists with "related artist" call
    for artist_id in recent_artists:
        response = requests.get(API_BASE_URL + 'artists/' + artist_id + "/related-artists", headers=headers)
        related_artists = response.json()
        one_removed.append(related_artists["artists"][random.randint(4, 8)]["id"])

    # now, for each once-removed artist, want to get twice-removed artists with "related artist" call (again)
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
        subset.append(related_artists["artists"][indices[0]]["id"])
        subset.append(related_artists["artists"][indices[1]]["id"])
        subset.append(related_artists["artists"][indices[2]]["id"])
        subset.append(related_artists["artists"][indices[3]]["id"])
        subset.append(related_artists["artists"][indices[4]]["id"])
        three_removed.append(subset)

    print(three_removed)

    # for printing purposes
    tuple_index = 0

    # for each group of recommendations
    for rec_group in three_removed:
        # NOTE: this is also just for printing purposes
        num = 1
        # for each specific id
        for rec_id in rec_group:
            # get the top tracks for that ID
            response = requests.get(API_BASE_URL + 'artists/' + rec_id + '/top-tracks', headers=headers)
            top_tracks = response.json()
            # artist may not have released 5 tracks, need to account for that
            released_tracks = len(top_tracks["tracks"])
            possible_tracks = min(released_tracks, 5)
            track_indices = random.sample(range(0, possible_tracks), possible_tracks)
            # go through each of the five top songs in random order, 
            # as soon as we find song that belongs to an album, add that album ...
            for index in track_indices: 
                if top_tracks["tracks"][index]['album']['album_type'] == 'album':
                        # NOTE: this is just for printing and will have to be changed for the actual program
                        if num == 1:
                            print("")
                            print("Because you enjoy " + recent_projects[tuple_index][0] + " by " + recent_projects[tuple_index][1] + ", please consider:")
                            tuple_index += 1
                        print(str(num) + ". " + top_tracks["tracks"][index]['album']['artists'][0]['name'] + " : " + top_tracks["tracks"][index]['album']["name"])
                        # NOTE: only want to add the first one, then no more ...
                        num += 1
                        break
                # if none of top tracks belong to album (ie, artist has not released one), 
                # then just recommend the "last" track as an album 
                elif index == track_indices[possible_tracks - 1]:
                    print(str(num) + ". " + top_tracks["tracks"][index]['album']['artists'][0]['name'] + " : " + top_tracks["tracks"][index]['album']["name"])
                    print("NOTE: THIS IS A SINGLE !!")

    return(jsonify(recent_albums))

# NOTE: oh yeah, can just store as a list of tuples

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
make the pages look a LOT better? -- see Flask manual
look for ways to speed up the program
loading page when we are generating the recs?
explain to user how spotify defines "recent" for albums (both added and listened to)
remove redundant code
'''
