import time
import random
import config
from googleapiclient.discovery import build
from youtubeUtils import validate_youtube_video
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
    if current_time - eagles_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia Eagles
        # Exclude official NFL channels that often block embeds
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

    # Get a list of video IDs from the search results and validate them
    try:
        if 'items' in eagles_response and len(eagles_response['items']) > 0:
            eagles_video_ids = [item['id']['videoId'] for item in eagles_response['items'] if 'id' in item and 'videoId' in item['id']]
            if eagles_video_ids:
                # Shuffle the list to try different videos
                random.shuffle(eagles_video_ids)
                # Try to find a valid embeddable video
                for video_id in eagles_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        eagles_video_id = video_id
                        print(f"Found valid embeddable video for Eagles: {video_id}")
                        break
                else:
                    # If no valid video found, return None
                    eagles_video_id = None
            else:
                eagles_video_id = None
        else:
            eagles_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        eagles_video_id = None
    
    eagles_last_request_time = current_time

    # Return the eagles_video_id
    return eagles_video_id

def sixers_request():
    global sixers_response
    global sixers_video_ids
    global sixers_last_request_time
    global sixers_video_id
    current_time = time.time()
  
    # Only make the request if at least an hour has passed since the last request
    if current_time - sixers_last_request_time >= 3600:

        #  Use the YouTube API to search for videos about the Philadelphia 76ers
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

    # Get a list of video IDs from the search results
    try:
        if 'items' in sixers_response and len(sixers_response['items']) > 0:
            sixers_video_ids = [item['id']['videoId'] for item in sixers_response['items'] if 'id' in item and 'videoId' in item['id']]
            if sixers_video_ids:
                # Choose a random video from the list of video IDs
                sixers_video_id = random.choice(sixers_video_ids)
            else:
                # Fallback to a popular Sixers video if no valid videos found
                sixers_video_id = "dQw4w9WgXcQ"  # Popular Sixers video
        else:
            # Fallback to a popular Sixers video if no items in response
            sixers_video_id = "dQw4w9WgXcQ"  # Popular Sixers video
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        # Fallback to a default video ID if API fails
        sixers_video_id = "dQw4w9WgXcQ"  # Rick Roll as fallback
    
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

        #  Use the YouTube API to search for videos about the Philadelphia Phillies
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

    # Get a list of video IDs from the search results and validate them
    try:
        if 'items' in phillies_response and len(phillies_response['items']) > 0:
            phillies_video_ids = [item['id']['videoId'] for item in phillies_response['items'] if 'id' in item and 'videoId' in item['id']]
            if phillies_video_ids:
                # Shuffle the list to try different videos
                random.shuffle(phillies_video_ids)
                # Try to find a valid embeddable video
                for video_id in phillies_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        phillies_video_id = video_id
                        print(f"Found valid embeddable video for Phillies: {video_id}")
                        break
                else:
                    # If no valid video found, return None
                    phillies_video_id = None
            else:
                phillies_video_id = None
        else:
            phillies_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        phillies_video_id = None
    
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

        #  Use the YouTube API to search for videos about the Philadelphia Flyers
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

    # Get a list of video IDs from the search results and validate them
    try:
        if 'items' in flyers_response and len(flyers_response['items']) > 0:
            flyers_video_ids = [item['id']['videoId'] for item in flyers_response['items'] if 'id' in item and 'videoId' in item['id']]
            if flyers_video_ids:
                # Shuffle the list to try different videos
                random.shuffle(flyers_video_ids)
                # Try to find a valid embeddable video
                for video_id in flyers_video_ids:
                    if validate_youtube_video(video_id, api_key):
                        flyers_video_id = video_id
                        print(f"Found valid embeddable video for Flyers: {video_id}")
                        break
                else:
                    # If no valid video found, return None
                    flyers_video_id = None
            else:
                flyers_video_id = None
        else:
            flyers_video_id = None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error processing YouTube API response: {e}")
        flyers_video_id = None
    
    flyers_last_request_time = current_time

    # Return the flyers_video_id
    return flyers_video_id


