import os
import random
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, redirect, request, jsonify, session, flash

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
Login with Spotify account.
'''
@app.route('/login')
def login():

    # what needs to be accessed
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
            'redirect_uri' : REDIRECT_URI + "/callback",
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

        return redirect('/track-things')


'''
Get recently saved albums, make recommendations.
    1. Get each of the five most recent albums in user's library.
    2. Now, for each album: 
        2a. Get the average statistics of songs.
        2b. Use /tracks/recommendations endpoint to get song recommendations, based on averages.
        2c. Iterate through songs, find the fist 20 albums that they belong to. 
        2d. Return randomly from this selection of 20 albums.
    3. Repeat 2. for all five albums. 
'''
@app.route('/track-things')
def track_things():
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

    # TODO: better error-catching
    try: 
        # get five most recently-listend to projects
        response = requests.get(API_BASE_URL + 'me/albums?limit=5&offset=0', headers=headers)
        recent_albums = response.json()
    except: 
        print(f"Error returned!!!")
        return "There is an error!!"

    # list of tuples 
    # first value is album id
    # second value is artist id
    # third value is comma-seperated string containing each song_id within album
    recent_albs_songs = []

    # go through each of five most recent albums
    for album in recent_albums["items"]:
        # get the first artist id
        artist_id = album["album"]["artists"][0]["id"]
        # each album must have at least one song_id
        # initiate string with that song_id
        track_ids_str = album["album"]["tracks"]["items"][0]["id"]
        # iterate through the rest of the song_ids, adding to string
        for track in album["album"]["tracks"]["items"][1:]:
            track_ids_str = track_ids_str + "," + track["id"]
        # finally, append completed tuple to list of tuples
        recent_albs_songs.append(tuple((album["album"]["id"], artist_id, track_ids_str)))

    print(recent_albs_songs)

    # iterate through each tuple of list
    for entry in recent_albs_songs:
        saved_album_id = entry[0]
        saved_artist_id = entry[1]
        song_ids = entry[2]
        # TODO: raise a better error
        try: 
            # get the audio features of every song on the album  
            response = requests.get(API_BASE_URL + 'audio-features?ids=' + song_ids, headers=headers)
            songs_info = response.json()
        except: 
            print(f"Error returned!!!")
            return "There is an error!!"
        
        # get the average statistics of each song on the album
        total_acousticness = 0
        total_danceability = 0
        total_instrumentalness = 0
        total_speechiness = 0
        total_valence = 0

        num_tracks = len(songs_info["audio_features"])

        for song in songs_info["audio_features"]:
            # print(song)
            total_acousticness += song['acousticness']
            total_danceability += song['danceability']
            total_instrumentalness += song['instrumentalness']
            total_speechiness += song['speechiness']
            total_valence += song['valence']

        avg_acousticness = total_acousticness / num_tracks
        avg_danceability = total_danceability / num_tracks
        avg_instrumentalness = total_instrumentalness / num_tracks
        avg_speechiness = total_speechiness / num_tracks
        avg_valence = total_valence / num_tracks

        # now, use these statistics to generate song recommendations
        request_str = ("recommendations?seed_artists=" + saved_artist_id + "&target_acousticness=" + 
                       str(avg_acousticness) + "&target_danceability=" + str(avg_danceability) + 
                       "&target_instrumentalness=" + str(avg_instrumentalness) + "&target_speechiness=" + 
                       str(avg_speechiness) + "&target_valence=" + str(avg_valence))
        try: 
            # get the song recommendations
            response = requests.get(API_BASE_URL + request_str, headers=headers)
            songs_info = response.json()
        except: 
            print(f"Error returned!!!")
            return "There is an error!!"
        
        # list of tuples, storing all possible recomendations (up to 20)
        # first value is recommended album_id
        # second value is recommended artist_id
        rec_albums_info = []
        # list of album ids so don't recommend same album twice
        rec_album_ids = []
        albums_added = 0 
        # now we have song info, get albums that they belong to
        for track in songs_info["tracks"]:
            rec_album_id = track['album']["id"]
            # want to recommend a NEW album
            if track["album"]["album_type"] == "ALBUM" and rec_album_id != saved_album_id and rec_album_id not in rec_album_ids:
                # add album_id, first artist_id
                # TODO: change from "name" to "id" for actual returns
                rec_albums_info.append(tuple((track["album"]["name"], track["album"]["artists"][0]["name"])))
                rec_album_ids.append(rec_album_id)
                albums_added += 1
            # stop once we reach 20
            if albums_added == 20:
                break

        # now, know that we have 20 saved albums, let's choose from those randomly
        # NOTE: we are assuming that at least five are going to be generated, which may not always be the case
        indices = random.sample(range(0, albums_added), 5)

        # NOTE: this will be removed 
        try: 
            # get the song recommendations
            response = requests.get(API_BASE_URL + "albums/" + saved_album_id, headers=headers)
            album_name = response.json()
        except: 
            print(f"Error returned!!!")
            return "There is an error!!"
        
        album_name = album_name["name"]

        # NOTE: just printing for now, but will eventually change to return to website
        print("Because you listend to " + album_name + ", we think you might enjoy:")
        for index in indices:
            print(rec_albums_info[index][0] + " by " + rec_albums_info[index][1])
        
        print("")

    return(jsonify(songs_info))

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
re-organize so that the endpoints are in different files (?) 
--> depends on how large the file gets, i feel like ~300 lines with comments isn't too bad
get this working on a real server (Render)
make the pages look a LOT better? -- see Flask manual
look for ways to speed up the program
loading page when we are generating the recs?
explain to user how spotify defines "recent" for albums (both added and listened to)
why can I not log Mom in?
'''
