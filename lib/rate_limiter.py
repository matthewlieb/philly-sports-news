import time
import random

from lib import config
from lib.youtube_utils import validate_youtube_video

# Set up the YouTube API client only if API key is configured
api_key = config.api_key
youtube = None
if api_key:
    try:
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        print(f"YouTube API init failed: {e}")
        youtube = None

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

def eagles_request():
    global eagles_response, eagles_video_ids, eagles_last_request_time, eagles_video_id
    current_time = time.time()
    if current_time - eagles_last_request_time >= 3600:
        if youtube:
            request = youtube.search().list(
                part="id,snippet",
                type='video',
                q='Philadelphia Eagles highlights news analysis 2024 2025 -NFL -"NFL Network" -"NFL.com"',
                videoDefinition='high',
                videoEmbeddable='true',
                order='relevance',
                publishedAfter='2024-01-01T00:00:00Z',
                maxResults=20,
                fields="items(id(videoId),snippet(title,channelTitle,publishedAt))"
            )
            eagles_response = request.execute()
        else:
            eagles_response = {}
    try:
        if not eagles_response:
            eagles_video_id = None
        elif 'items' in eagles_response and len(eagles_response['items']) > 0:
            eagles_video_ids = [item['id']['videoId'] for item in eagles_response['items'] if 'id' in item and 'videoId' in item['id']]
            if eagles_video_ids:
                random.shuffle(eagles_video_ids)
                for video_id in eagles_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        eagles_video_id = video_id
                        print(f"Found valid embeddable video for Eagles: {video_id}")
                        break
                else:
                    eagles_video_id = None
            else:
                eagles_video_id = None
        else:
            eagles_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        eagles_video_id = None
    eagles_last_request_time = current_time
    return eagles_video_id

def sixers_request():
    global sixers_response, sixers_video_ids, sixers_last_request_time, sixers_video_id
    current_time = time.time()
    if current_time - sixers_last_request_time >= 3600:
        if youtube:
            request = youtube.search().list(
                part="id,snippet",
                type='video',
                q='Philadelphia 76ers highlights news analysis 2024 2025 NBA',
                videoDefinition='high',
                videoEmbeddable='true',
                order='relevance',
                publishedAfter='2024-01-01T00:00:00Z',
                maxResults=20,
                fields="items(id(videoId),snippet(title,channelTitle,publishedAt))"
            )
            sixers_response = request.execute()
        else:
            sixers_response = {}
    try:
        if not sixers_response:
            sixers_video_id = None
        elif 'items' in sixers_response and len(sixers_response['items']) > 0:
            sixers_video_ids = [item['id']['videoId'] for item in sixers_response['items'] if 'id' in item and 'videoId' in item['id']]
            if sixers_video_ids:
                random.shuffle(sixers_video_ids)
                for video_id in sixers_video_ids:
                    if api_key and validate_youtube_video(video_id, api_key):
                        sixers_video_id = video_id
                        break
                else:
                    sixers_video_id = None
            else:
                sixers_video_id = None
        else:
            sixers_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        sixers_video_id = None
    sixers_last_request_time = current_time
    return sixers_video_id

def phillies_request():
    global phillies_response, phillies_video_ids, phillies_last_request_time, phillies_video_id
    current_time = time.time()
    if current_time - phillies_last_request_time >= 3600:
        if youtube:
            request = youtube.search().list(
                part="id,snippet",
                type='video',
                q='Philadelphia Phillies highlights news analysis 2024 2025 MLB',
                videoDefinition='high',
                videoEmbeddable='true',
                order='relevance',
                publishedAfter='2024-01-01T00:00:00Z',
                maxResults=20,
                fields="items(id(videoId),snippet(title,channelTitle,publishedAt))"
            )
            phillies_response = request.execute()
        else:
            phillies_response = {}
    try:
        if not phillies_response:
            phillies_video_id = None
        elif 'items' in phillies_response and len(phillies_response['items']) > 0:
            phillies_video_ids = [item['id']['videoId'] for item in phillies_response['items'] if 'id' in item and 'videoId' in item['id']]
            if phillies_video_ids:
                random.shuffle(phillies_video_ids)
                for video_id in phillies_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        phillies_video_id = video_id
                        print(f"Found valid embeddable video for Phillies: {video_id}")
                        break
                else:
                    phillies_video_id = None
            else:
                phillies_video_id = None
        else:
            phillies_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        phillies_video_id = None
    phillies_last_request_time = current_time
    return phillies_video_id

def flyers_request():
    global flyers_response, flyers_video_ids, flyers_last_request_time, flyers_video_id
    current_time = time.time()
    if current_time - flyers_last_request_time >= 3600:
        if youtube:
            request = youtube.search().list(
                part="id,snippet",
                type='video',
                q='Philadelphia Flyers highlights news analysis 2024 2025 NHL',
                videoDefinition='high',
                videoEmbeddable='true',
                order='relevance',
                publishedAfter='2024-01-01T00:00:00Z',
                maxResults=20,
                fields="items(id(videoId),snippet(title,channelTitle,publishedAt))"
            )
            flyers_response = request.execute()
        else:
            flyers_response = {}
    try:
        if not flyers_response:
            flyers_video_id = None
        elif 'items' in flyers_response and len(flyers_response['items']) > 0:
            flyers_video_ids = [item['id']['videoId'] for item in flyers_response['items'] if 'id' in item and 'videoId' in item['id']]
            if flyers_video_ids:
                random.shuffle(flyers_video_ids)
                for video_id in flyers_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        flyers_video_id = video_id
                        print(f"Found valid embeddable video for Flyers: {video_id}")
                        break
                else:
                    flyers_video_id = None
            else:
                flyers_video_id = None
        else:
            flyers_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        flyers_video_id = None
    flyers_last_request_time = current_time
    return flyers_video_id
