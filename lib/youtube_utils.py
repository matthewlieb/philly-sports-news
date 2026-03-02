"""
Utility functions for YouTube video handling
"""

import requests
import time
from datetime import datetime, timedelta, timezone

def validate_youtube_video(video_id, api_key):
    """
    Validate that a YouTube video ID is embeddable, available, and not blocked
    Returns True if video can be embedded and played, False otherwise
    Also checks for content that might be blocked by owners (like NFL)
    """
    try:
        from googleapiclient.discovery import build
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Get video details including snippet to check channel and content
        request = youtube.videos().list(
            part='status,contentDetails,snippet',
            id=video_id
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            video = response['items'][0]
            video_status = video.get('status', {})
            content_details = video.get('contentDetails', {})
            snippet = video.get('snippet', {})
            
            # Check if video is embeddable and public
            is_embeddable = video_status.get('embeddable', False)
            is_public = video_status.get('privacyStatus') == 'public'
            
            # If video is not embeddable or not public, return False
            if not is_embeddable or not is_public:
                return False
            
            # Check for content restrictions (region blocking, etc.)
            region_restriction = content_details.get('regionRestriction', {})
            blocked_regions = region_restriction.get('blocked', [])
            
            # Check if video is blocked in common regions (US, CA, etc.)
            if blocked_regions and ('US' in blocked_regions or 'CA' in blocked_regions):
                return False
            
            # Check channel name - exclude official NFL/NBA/MLB/NHL channels that often block embeds
            channel_title = snippet.get('channelTitle', '').lower()
            blocked_channels = ['nfl', 'nba', 'mlb', 'nhl', 'espn', 'fox sports', 'cbs sports']
            if any(blocked in channel_title for blocked in blocked_channels):
                print(f"Excluding video from blocked channel: {channel_title}")
                return False
            
            # Check video title for NFL/NBA/MLB/NHL official content indicators
            video_title = snippet.get('title', '').lower()
            if 'nfl' in video_title and any(word in channel_title for word in ['official', 'nfl network', 'nfl.com']):
                print(f"Excluding likely blocked NFL content: {video_title}")
                return False
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error validating YouTube video {video_id}: {e}")
        return False

def get_embeddable_video_id(team, api_key, max_attempts=20):
    """
    Get a valid, embeddable YouTube video ID for a team
    Returns a valid video ID or None if none found
    Tries multiple videos until finding one that is actually playable
    """
    try:
        from googleapiclient.discovery import build
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Define search terms for each team - no static years, dates handled by publishedAfter
        # videoCategoryId=17 (Sports) filters out music videos, etc.
        search_terms = {
            'eagles': 'Philadelphia Eagles NFL highlights news analysis -music -"Eagles band"',
            'sixers': 'Philadelphia 76ers NBA highlights news analysis',
            'phillies': 'Philadelphia Phillies MLB highlights news analysis',
            'flyers': 'Philadelphia Flyers NHL highlights news analysis'
        }
        
        search_term = search_terms.get(team.lower(), 'Philadelphia sports highlights')
        published_after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Search for videos - order=date for recent results
        request = youtube.search().list(
            part="id,snippet",
            type='video',
            q=search_term,
            videoCategoryId='17',  # Sports only
            videoDefinition='high',
            videoEmbeddable='true',
            order='date',
            publishedAfter=published_after,
            maxResults=max_attempts,
            fields="items(id(videoId),snippet(title,channelTitle,publishedAt))"
        )
        
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            # Try to find a valid embeddable video by checking each one
            for item in response['items']:
                video_id = item['id']['videoId']
                if validate_youtube_video(video_id, api_key):
                    print(f"Found valid embeddable video for {team}: {video_id}")
                    return video_id
            
            # If no valid video found after checking all, return None
            print(f"Warning: No valid embeddable videos found for {team} after checking {len(response['items'])} videos")
            return None
        
        return None
        
    except Exception as e:
        print(f"Error getting YouTube video for {team}: {e}")
        return None

def create_safe_embed_code(video_id, team):
    """
    Create a simple YouTube embed code - original format
    Only returns embed code if video_id is valid, otherwise returns empty string
    """
    if not video_id or video_id == "dQw4w9WgXcQ":  # None or invalid video
        # Return empty string - don't display anything
        return ''
    
    # Return simple iframe embed - original format
    return f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
