import time
import random
import config
from googleapiclient.discovery import build
# Set up the YouTube API client
api_key = config.api_key
youtube = build('youtube', 'v3', developerKey=api_key)

# Initialize variables
eagles_last_request_time = 0
eagles_video_id = None
eagles_video_ids = None
eagles_response = None

sixers_last_request_time = 0
sixers_video_id = None
sixers_video_ids = None
sixers_response = None

phillies_last_request_time = 0
phillies_video_id = None
phillies_video_ids = None
phillies_response = None

flyers_last_request_time = 0
flyers_video_id = None
flyers_video_ids = None
flyers_response = None

#Limiter functions for YouTube requests
def eagles_request():
    global eagles_response
    global eagles_video_ids
    global eagles_last_request_time
    global eagles_video_id
    current_time = time.time()
  
    # Only make the request if at least an hour has passed since the last request
    if current_time - sixers_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia Eagles
        request = youtube.search().list(
            part="id",
            type='video',
            q='Philadelphia Eagles',
            videoDefinition='high',
            #videoLicense='creativeCommon',
            videoEmbeddable='true', 
            maxResults=20,
            fields="items(id(videoId))"
        )
        eagles_response = request.execute()

    # Get a list of video IDs from the search results
    eagles_video_ids = [item['id']['videoId'] for item in eagles_response['items']]

    # Choose a random video from the list of video IDs
    eagles_video_id = random.choice(eagles_video_ids)
    eagles_last_request_time = current_time

    # Return the sixers_video_id
    return eagles_video_id

def sixers_request():
    global sixers_response
    global sixers_video_ids
    global sixers_last_request_time
    global sixers_video_id
    current_time = time.time()
  
    # Only make the request if at least an hour has passed since the last request
    if current_time - sixers_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia Eagles
        request = youtube.search().list(
            part="id",
            type='video',
            q='Philadelphia 76ers',
            videoDefinition='high',
            videoEmbeddable='true', 
            maxResults=20,
            fields="items(id(videoId))"
        )
        sixers_response = request.execute()

    # Get a list of video IDs from the search results
    sixers_video_ids = [item['id']['videoId'] for item in sixers_response['items']]

    # Choose a random video from the list of video IDs
    sixers_video_id = random.choice(sixers_video_ids)
    sixers_last_request_time = current_time

    # Return the sixers_video_id
    return sixers_video_id

def phillies_request():
    global phillies_response
    global phillies_video_ids
    global phillies_last_request_time
    global phillies_video_id
    current_time = time.time()
  
    # Only make the request if at least an hour has passed since the last request
    if current_time - phillies_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia Eagles
        request = youtube.search().list(
            part="id",
            type='video',
            q='Philadelphia Phillies',
            videoDefinition='high',
            videoEmbeddable='true', 
            maxResults=20,
            fields="items(id(videoId))"
        )
        phillies_response = request.execute()

    # Get a list of video IDs from the search results
    phillies_video_ids = [item['id']['videoId'] for item in phillies_response['items']]

    # Choose a random video from the list of video IDs
    phillies_video_id = random.choice(phillies_video_ids)
    phillies_last_request_time = current_time

    # Return the phillies_video_id
    return phillies_video_id

def flyers_request():
    global flyers_response
    global flyers_video_ids
    global flyers_last_request_time
    global flyers_video_id
    current_time = time.time()
  
    # Only make the request if at least an hour has passed since the last request
    if current_time - flyers_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia Eagles
        request = youtube.search().list(
            part="id",
            type='video',
            q='Philadelphia Flyers',
            videoDefinition='high',
            videoEmbeddable='true', 
            maxResults=20,
            fields="items(id(videoId))"
        )
        flyers_response = request.execute()

    # Get a list of video IDs from the search results
    flyers_video_ids = [item['id']['videoId'] for item in flyers_response['items']]

    # Choose a random video from the list of video IDs
    flyers_video_id = random.choice(flyers_video_ids)
    flyers_last_request_time = current_time

    # Return the flyers_video_id
    return flyers_video_id


