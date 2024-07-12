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
    
    # get five most recently listened-to projects
    try: 
        response = requests.get(API_BASE_URL + 'me/albums?limit=5&offset=0', headers=headers)
        recent_albums = response.json()
    except: 
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        # if hit rate limit, explain to use   
        # NOTE: should content also be returned in the HTML? not sure if that is good practice tbh.
        print(response.content)
        if response.status_code == 429: 
            return render_template('error/rate_limit.html')
        return render_template('error/error.html')
      
    # check if user has zero albums ... tell them that they need to save some and what no
    if len(recent_albums["items"]) == 0:
        return render_template("error/nothing.html")

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

    content = []

    # iterate through each tuple of list
    for entry in recent_albs_songs:
        saved_album_id = entry[0]
        saved_artist_id = entry[1]
        song_ids = entry[2]

        # get the audio features of every song on the album  
        try: 
            response = requests.get(API_BASE_URL + 'audio-features?ids=' + song_ids, headers=headers)
            songs_info = response.json()
        except: 
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(response.content)
            # if hit rate limit, explain to user
            if response.status_code == 429: 
                return render_template('error/rate_limit.html')
            return render_template('error/error.html')
        
        # get the average statistics of each song on the album
        total_acousticness = 0
        total_danceability = 0
        total_instrumentalness = 0
        total_speechiness = 0
        total_valence = 0

        num_tracks = len(songs_info["audio_features"])

        # NOTE: have to account for interludes (short songs/skits) -- they won't have information on them
        num_interludes = 0
        
        for song in songs_info["audio_features"]:
            if song is not None:
                total_acousticness += song['acousticness']
                total_danceability += song['danceability']
                total_instrumentalness += song['instrumentalness']
                total_speechiness += song['speechiness']
                total_valence += song['valence']
            else: 
                num_interludes += 1

        avg_acousticness = total_acousticness / (num_tracks - num_interludes)
        avg_danceability = total_danceability / (num_tracks - num_interludes)
        avg_instrumentalness = total_instrumentalness / (num_tracks - num_interludes)
        avg_speechiness = total_speechiness / (num_tracks - num_interludes)
        avg_valence = total_valence / (num_tracks - num_interludes)

        # now, use these statistics to generate song recommendations
        request_str = ("recommendations?seed_artists=" + saved_artist_id + "&target_acousticness=" + 
                       str(avg_acousticness) + "&target_danceability=" + str(avg_danceability) + 
                       "&target_instrumentalness=" + str(avg_instrumentalness) + "&target_speechiness=" + 
                       str(avg_speechiness) + "&target_valence=" + str(avg_valence))
        print("API_BASE_URL: ", API_BASE_URL)
        print("request_str: ", request_str)
        print("headers: ", headers)

        try: 
            # get the song recommendations
            response = requests.get(API_BASE_URL + request_str, headers=headers)
            songs_info = response.json()
        except: 
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(response.content)
            # if hit rate limit, explain to user
            if response.status_code == 429: 
                return render_template('error/rate_limit.html')
            return render_template('error/error.html')
        
        '''
        list of tuples, storing all possible recomendations (up to 20)
        first value is recommended album name
        second value is recommended artist name
        third value is link to album image
        fourth value is link to album in spotify player
        '''
        rec_albums_info = []
        # list of album ids so don't recommend same album twice
        rec_album_ids = []
        albums_added = 0 
        # now we have song info, get albums that they belong to
        for track in songs_info["tracks"]:
            rec_album_id = track['album']["id"]
            # want to recommend a NEW album
            if track["album"]["album_type"] == "ALBUM" and rec_album_id != saved_album_id and rec_album_id not in rec_album_ids:
                album_name = track["album"]["name"]
                artist_name = track["album"]["artists"][0]["name"]
                # TODO: change from "name" to "id" for actual returns
                album_image = track["album"]["images"][1]["url"]
                album_link = track["album"]["external_urls"].get("spotify") + "?" + track["album"]["uri"] + "&go=1"
                print("album_link: ", album_link)
                rec_albums_info.append(tuple((album_name, artist_name, album_image, album_link)))
                rec_album_ids.append(rec_album_id)
                albums_added += 1
            # stop once we reach 20
            if albums_added == 20:
                break

        # now, know that we have 20 saved albums, let's choose from those randomly
        # NOTE: we are assuming that at least five are going to be generated, which may not always be the case
        indices = random.sample(range(0, albums_added), 6)

        # have to store the original album/artist name, then have to get the image for each album
        # get the song recommendations
        try: 
            response = requests.get(API_BASE_URL + "albums/" + saved_album_id, headers=headers)
            album_info = response.json()
        except: 
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(response.content)
            # if hit rate limit, explain to user
            if response.status_code == 429: 
                return render_template('error/rate_limit.html')
            return render_template('error/error.html')
        
        album_name = album_info["name"]
        artist_name = album_info["artists"][0]["name"]
        
        content.append({"type":"text", "data":"Because you listened to <b> " + album_name + " </b> by <b> " + artist_name + "</b>, we think you might enjoy:"})
        for index in indices: 
            image_html = f'<a href="{rec_albums_info[index][3]}" target="_blank"><img src="{rec_albums_info[index][2]}" width="200" height="200"></a>'
            content.append({"type":"album", "image":image_html, "text":rec_albums_info[index][0] + " by " + rec_albums_info[index][1]})
    
    return render_template('rec/recs.html', content=content)
