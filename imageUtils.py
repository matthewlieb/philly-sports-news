"""
Utility functions for handling images and fallbacks
"""

def get_team_fallback_image(team):
    """Get the appropriate fallback image for each team"""
    fallback_images = {
        'eagles': 'static/phillySportsNewsEagles.png',
        'sixers': 'static/phillySportsNewsSixers.png', 
        'phillies': 'static/phillySportsNewsPhillies.png',
        'flyers': 'static/phillySportsNewsFlyers.png'
    }
    return fallback_images.get(team.lower(), 'static/phillySportsNewsEagles.png')

def process_image_url(image_url, team):
    """Process image URL and return fallback if needed"""
    if not image_url or image_url == 'None' or image_url == '':
        return get_team_fallback_image(team)
    
    # Ensure the URL is complete
    if image_url.startswith('//'):
        return 'https:' + image_url
    elif not image_url.startswith('http'):
        return 'https://' + image_url
    
    return image_url

def get_image_with_fallback(image_url, team, onerror_js=None):
    """Generate HTML img tag with proper fallback"""
    fallback = get_team_fallback_image(team)
    if onerror_js is None:
        onerror_js = f"this.src='{fallback}'"
    
    processed_url = process_image_url(image_url, team)
    
    return f'<img class="card-img-top" src="{processed_url}" alt="{team.title()} News" onerror="{onerror_js}">'
