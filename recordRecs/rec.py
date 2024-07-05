import os
import random
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Blueprint, flash, g, redirect, render_template, request, jsonify, session, url_for
)

bp = Blueprint("rec", __name__, url_prefix="/")

# load environment variables
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET =os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
AUTH_URL = os.getenv('AUTH_URL')
TOKEN_URL = os.getenv('TOKEN_URL')
API_BASE_URL = os.getenv('API_BASE_URL')

@bp.route("/recs")
def recs():
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
        # get five most recently-listened to projects
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

    # print(recent_albs_songs)
    content = []

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
        
        # NOTE: have to get the images of the albums in this little thing as well from what i understand
        
        # list of tuples, storing all possible recomendations (up to 20)
        # first value is recommended album_id
        # second value is recommended artist_id
        # third value is link to album image
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
                rec_albums_info.append(tuple((track["album"]["name"], track["album"]["artists"][0]["name"], track["album"]["images"][1]["url"])))
                rec_album_ids.append(rec_album_id)
                albums_added += 1
            # stop once we reach 20
            if albums_added == 20:
                break

        # now, know that we have 20 saved albums, let's choose from those randomly
        # NOTE: we are assuming that at least five are going to be generated, which may not always be the case
        indices = random.sample(range(0, albums_added), 6)

        # NOTE: this will be removed, just getting the name for now (I think)
        # NOTE: can get the images from here, so this might actually be a good idea tbh ...
        # have to store the original album/artist name, then have to get the image for each album
        # that we are looking through as well for some reason I think tbh.
        try: 
            # get the song recommendations
            response = requests.get(API_BASE_URL + "albums/" + saved_album_id, headers=headers)
            album_info = response.json()
        except: 
            print(f"Error returned!!!")
            return "There is an error!!"
        
        album_name = album_info["name"]
        artist_name = album_info["artists"][0]["name"]

        # NOTE: just printing for now, but will eventually change to return to website
        # print("Because you listend to " + album_name + " by " + artist_name + ", we think you might enjoy:")
        # for index in indices:
            # print(rec_albums_info[index][0] + " by " + rec_albums_info[index][1])
        
        # print("")

        content.append({"type":"text", "data":"<b>Because you listend to " + album_name + " by " + artist_name + ", we think you might enjoy:</b>"})
        for index in indices: 
            content.append({"type":"image", "data":rec_albums_info[index][2]})
            content.append({"type":"text", "data":rec_albums_info[index][0] + " by " + rec_albums_info[index][1]})

    # return(jsonify(songs_info))
    return render_template('rec/recs.html', content=content)
# TODO: create the waiting page that comes in between the first click and the input generation 
# (or something like that and what not and all of that jazz don't talk to me bruh I am the man and what not.)
# Ok so as it turns out the loading thing is kind of complicated so i may deal with the later tbh
# should also determine what I want the general style of the webpage to be and what not.


'''
can just create a list of "content", and then return that at the end of the text of something like that
not sure if this is the best way to go about things but it does seem efficient and what not.
so yeah i know exactly the format of what i am going to be returning every time, 
so i can just append to content as needed, and then return content at the end with the return statement and what not. 

it would be cool if you could also click on the images and get to the spotify page that hosts them and what not. 
'''
