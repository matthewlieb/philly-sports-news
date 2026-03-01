# Load .env so API_KEY and other vars are available (e.g. for YouTube embeds)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Fallback: if python-dotenv not installed, load .env manually from project root
import os as _os
_env_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".env")
if _os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip().strip("'\"").strip()
                if _k and _v and _k not in _os.environ:
                    _os.environ[_k] = _v
                    if _k == "api_key":
                        _os.environ["API_KEY"] = _v

import random
from typing import List, Tuple
from jinja2 import Template
from lib.rate_limiter import *
from lib.youtube_utils import get_embeddable_video_id, create_safe_embed_code
from flask import Flask
from flask_caching import Cache
from utils.article_filter import filter_complete_articles, get_source_name_from_url, merge_and_rank_articles
import lib.config as config

from scrapers.source_collectors import collect_articles_for_team
from lib.article_enhancer import enhance_article_data

app = Flask(__name__)

# Configure caching
app.config['CACHE_TYPE'] = 'simple'  # Simple in-memory cache
app.config['CACHE_DEFAULT_TIMEOUT'] = 3600  # 1 hour default timeout
cache = Cache(app)

def filter_articles_with_images(titles, urls, images, blurbs, authors=None):
    """
    Filter articles to only include those with valid images (backward compatibility).
    Now uses the new quality-based filtering system.
    """
    return filter_complete_articles(titles, urls, images, blurbs, authors, min_score=70)


def merge_articles_from_sources(article_sources: List[dict]) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """
    Merge articles from multiple sources and return only fully populated ones.
    
    Args:
        article_sources: List of dicts with keys: titles, urls, images, blurbs, authors
        
    Returns:
        Merged and filtered (titles, urls, images, blurbs, authors) lists
    """
    all_articles = []
    
    # Collect all articles from all sources
    for source in article_sources:
        titles = source.get('titles', [])
        urls = source.get('urls', [])
        images = source.get('images', [])
        blurbs = source.get('blurbs', [])
        authors = source.get('authors', [])
        
        # Ensure all lists are same length
        max_len = max(len(titles), len(urls), len(images), len(blurbs))
        if authors:
            max_len = max(max_len, len(authors))
        
        for i in range(max_len):
            article = {
                'title': titles[i] if i < len(titles) else "",
                'url': urls[i] if i < len(urls) else "",
                'image': images[i] if i < len(images) else None,
                'description': blurbs[i] if i < len(blurbs) else "",
                'author': authors[i] if authors and i < len(authors) else None,
                'source': get_source_name_from_url(urls[i] if i < len(urls) else "")
            }
            all_articles.append(article)
    
    # Rank and filter articles by quality
    ranked_articles = merge_and_rank_articles(all_articles, max_articles=30)
    
    # Extract lists
    filtered_titles = [a['title'] for a in ranked_articles]
    filtered_urls = [a['url'] for a in ranked_articles]
    filtered_images = [a['image'] for a in ranked_articles]
    filtered_blurbs = [a['description'] for a in ranked_articles]
    
    # Ensure all authors have "-- " prefix for consistency
    filtered_authors = []
    for article in ranked_articles:
        author = article.get('author') or article.get('source', 'Unknown')
        # Add "-- " prefix if not already present
        if author and not author.startswith('-- '):
            if author == 'Unknown' or author == 'None':
                filtered_authors.append('-- Unknown')
            else:
                filtered_authors.append(f'-- {author}')
        else:
            filtered_authors.append(author if author else '-- Unknown')
    
    return filtered_titles, filtered_urls, filtered_images, filtered_blurbs, filtered_authors

@app.route('/health')
def health():
    """Lightweight health check; no scraping. Use for Heroku/load balancer."""
    return 'ok', 200

def create_dict(titles, urls):

    return {k: v for k, v in zip(titles[:5], urls[:5])}

@cache.cached(timeout=3600, key_prefix='eagles_articles')
def get_eagles_articles():
    """
    Get Eagles articles with caching. Fetches on demand from all sources.
    Cache expires after 1 hour.
    """
    article_sources = collect_articles_for_team("eagles")
    if not article_sources:
        return [], [], [], [], []
    merged = merge_articles_from_sources(article_sources)
    # Optionally enhance top articles for better images/descriptions
    titles, urls, images, blurbs, authors = merged
    if titles and urls:
        titles, urls, images, blurbs, authors = enhance_article_data(
            titles, urls, images, blurbs, authors, max_enhance=10, enhance_all=True
        )
    return titles, urls, images, blurbs, authors

@app.route('/')
def home():
    # Get cached articles (or fetch if cache miss)
    merged_titles, merged_urls, merged_images, merged_blurbs, merged_authors = get_eagles_articles()
    
    # Distribute across 5 columns
    num_per_column = 4
    filtered_titles1 = merged_titles[:num_per_column]
    filtered_titles2 = merged_titles[num_per_column:num_per_column*2]
    filtered_titles3 = merged_titles[num_per_column*2:num_per_column*3]
    filtered_titles4 = merged_titles[num_per_column*3:num_per_column*4]
    filtered_titles5 = merged_titles[num_per_column*4:num_per_column*5] if len(merged_titles) > num_per_column*4 else []
    
    filtered_urls1 = merged_urls[:num_per_column]
    filtered_urls2 = merged_urls[num_per_column:num_per_column*2]
    filtered_urls3 = merged_urls[num_per_column*2:num_per_column*3]
    filtered_urls4 = merged_urls[num_per_column*3:num_per_column*4]
    filtered_urls5 = merged_urls[num_per_column*4:num_per_column*5] if len(merged_urls) > num_per_column*4 else []
    
    filtered_images1 = merged_images[:num_per_column]
    filtered_images2 = merged_images[num_per_column:num_per_column*2]
    filtered_images3 = merged_images[num_per_column*2:num_per_column*3]
    filtered_images4 = merged_images[num_per_column*3:num_per_column*4]
    filtered_images5 = merged_images[num_per_column*4:num_per_column*5] if len(merged_images) > num_per_column*4 else []
    
    filtered_blurbs1 = merged_blurbs[:num_per_column]
    filtered_blurbs2 = merged_blurbs[num_per_column:num_per_column*2]
    filtered_blurbs3 = merged_blurbs[num_per_column*2:num_per_column*3]
    filtered_blurbs4 = merged_blurbs[num_per_column*3:num_per_column*4]
    filtered_blurbs5 = merged_blurbs[num_per_column*4:num_per_column*5] if len(merged_blurbs) > num_per_column*4 else []
    
    filtered_authors1 = merged_authors[:num_per_column]
    filtered_authors2 = merged_authors[num_per_column:num_per_column*2]
    filtered_authors3 = merged_authors[num_per_column*2:num_per_column*3]
    filtered_authors4 = merged_authors[num_per_column*3:num_per_column*4]
    filtered_authors5 = merged_authors[num_per_column*4:num_per_column*5] if len(merged_authors) > num_per_column*4 else []

    dict1 = create_dict(filtered_titles1, filtered_urls1)
    dict2 = create_dict(filtered_titles2, filtered_urls2)
    dict3 = create_dict(filtered_titles3, filtered_urls3)
    dict4 = create_dict(filtered_titles4, filtered_urls4)
    dict5 = create_dict(filtered_titles5, filtered_urls5)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}
   
    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    # Create a new dictionary from the shuffled list
    shuffled_dict = dict(combined_list)
    keys = list(shuffled_dict.keys())
    values = list(shuffled_dict.values())

    # Get a valid embeddable YouTube video
    video_id = eagles_request()
    embed_code = create_safe_embed_code(video_id, 'Philadelphia Eagles')

    # Read the contents of the template file into a string
    with open('templates/index.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the filtered headlines and URLs
    html = template.render(zip=zip, column1=filtered_titles1, column2=filtered_titles2, column3=filtered_titles3, column4=filtered_titles4, column5=filtered_titles5, urls1=filtered_urls1, urls2=filtered_urls2, urls3=filtered_urls3, urls4=filtered_urls4, urls5=filtered_urls5, imageURLS1=filtered_images1, imageURLS2=filtered_images2, imageURLS3=filtered_images3, imageURLS4=filtered_images4, imageURLS5=filtered_images5, keys=keys, values=values, embed_code=embed_code, blurbs1=filtered_blurbs1, blurbs2=filtered_blurbs2, blurbs3=filtered_blurbs3, blurbs4=filtered_blurbs4, blurbs5=filtered_blurbs5, authors1=filtered_authors1, authors2=filtered_authors2, authors3=filtered_authors3, authors4=filtered_authors4, authors5=filtered_authors5)

    return html

@cache.cached(timeout=3600, key_prefix='sixers_articles')
def get_sixers_articles():
    """
    Get Sixers articles with caching. Fetches on demand from all sources.
    """
    article_sources = collect_articles_for_team("sixers")
    if not article_sources:
        return [], [], [], [], []
    merged = merge_articles_from_sources(article_sources)
    titles, urls, images, blurbs, authors = merged
    if titles and urls:
        titles, urls, images, blurbs, authors = enhance_article_data(
            titles, urls, images, blurbs, authors, max_enhance=10, enhance_all=True
        )
    return titles, urls, images, blurbs, authors

@app.route('/sixers')
def sixers():
    # Get cached articles (or fetch if cache miss)
    merged_titles, merged_urls, merged_images, merged_blurbs, merged_authors = get_sixers_articles()
    
    # Take top 20 articles and distribute them across the 5 columns
    # This ensures we always have fully populated articles, regardless of source
    num_per_column = 4
    filtered_titles1a = merged_titles[:num_per_column]
    filtered_titles2a = merged_titles[num_per_column:num_per_column*2]
    filtered_titles3a = merged_titles[num_per_column*2:num_per_column*3]
    filtered_titles4a = merged_titles[num_per_column*3:num_per_column*4]
    filtered_titles5a = merged_titles[num_per_column*4:num_per_column*5] if len(merged_titles) > num_per_column*4 else []
    
    filtered_urls1a = merged_urls[:num_per_column]
    filtered_urls2a = merged_urls[num_per_column:num_per_column*2]
    filtered_urls3a = merged_urls[num_per_column*2:num_per_column*3]
    filtered_urls4a = merged_urls[num_per_column*3:num_per_column*4]
    filtered_urls5a = merged_urls[num_per_column*4:num_per_column*5] if len(merged_urls) > num_per_column*4 else []
    
    filtered_images1a = merged_images[:num_per_column]
    filtered_images2a = merged_images[num_per_column:num_per_column*2]
    filtered_images3a = merged_images[num_per_column*2:num_per_column*3]
    filtered_images4a = merged_images[num_per_column*3:num_per_column*4]
    filtered_images5a = merged_images[num_per_column*4:num_per_column*5] if len(merged_images) > num_per_column*4 else []
    
    filtered_blurbs1a = merged_blurbs[:num_per_column]
    filtered_blurbs2a = merged_blurbs[num_per_column:num_per_column*2]
    filtered_blurbs3a = merged_blurbs[num_per_column*2:num_per_column*3]
    filtered_blurbs4a = merged_blurbs[num_per_column*3:num_per_column*4]
    filtered_blurbs5a = merged_blurbs[num_per_column*4:num_per_column*5] if len(merged_blurbs) > num_per_column*4 else []
    
    filtered_authors1a = merged_authors[:num_per_column]
    filtered_authors2a = merged_authors[num_per_column:num_per_column*2]
    filtered_authors3a = merged_authors[num_per_column*2:num_per_column*3]
    filtered_authors4a = merged_authors[num_per_column*3:num_per_column*4]
    filtered_authors5a = merged_authors[num_per_column*4:num_per_column*5] if len(merged_authors) > num_per_column*4 else []

    dict1 = create_dict(filtered_titles1a, filtered_urls1a)
    dict2 = create_dict(filtered_titles2a, filtered_urls2a)
    dict3 = create_dict(filtered_titles3a, filtered_urls3a)
    dict4 = create_dict(filtered_titles4a, filtered_urls4a)
    dict5 = create_dict(filtered_titles5a, filtered_urls5a)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}
   
    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    # Create a new dictionary from the shuffled list
    shuffled_dict = dict(combined_list)
    keys1 = list(shuffled_dict.keys())
    values1 = list(shuffled_dict.values())

    video_id = None
    if config.api_key:
        video_id = get_embeddable_video_id('sixers', config.api_key)
    embed_code1 = create_safe_embed_code(video_id, 'Philadelphia 76ers')

    # Read the contents of the template file into a string
    with open('templates/index2a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the filtered headlines and URLs
    # Note: Source names are now dynamic based on article URLs
    html2 = template.render(zip1=zip, column1a=filtered_titles1a, column2a=filtered_titles2a, column3a=filtered_titles3a, column4a=filtered_titles4a, column5a=filtered_titles5a, urls1a=filtered_urls1a, urls2a=filtered_urls2a, urls3a=filtered_urls3a, urls4a=filtered_urls4a, urls5a=filtered_urls5a, imageURLS1a=filtered_images1a, imageURLS2a=filtered_images2a, imageURLS3a=filtered_images3a, imageURLS4a=filtered_images4a, imageURLS5a=filtered_images5a, keys1=keys1, values1=values1, embed_code1=embed_code1, blurbs1a=filtered_blurbs1a, blurbs2a=filtered_blurbs2a, blurbs3a=filtered_blurbs3a, blurbs4a=filtered_blurbs4a, blurbs5a=filtered_blurbs5a, authors1a=filtered_authors1a, authors2a=filtered_authors2a, authors3a=filtered_authors3a, authors4a=filtered_authors4a, authors5a=filtered_authors5a)

    return html2

@cache.cached(timeout=3600, key_prefix='phillies_articles')
def get_phillies_articles():
    """
    Get Phillies articles with caching. Fetches on demand from all sources.
    """
    article_sources = collect_articles_for_team("phillies")
    if not article_sources:
        return [], [], [], [], []
    merged = merge_articles_from_sources(article_sources)
    titles, urls, images, blurbs, authors = merged
    if titles and urls:
        titles, urls, images, blurbs, authors = enhance_article_data(
            titles, urls, images, blurbs, authors, max_enhance=10, enhance_all=True
        )
    return titles, urls, images, blurbs, authors

@app.route('/phillies')
def phillies():
    # Get cached articles (or fetch if cache miss)
    merged_titles, merged_urls, merged_images, merged_blurbs, merged_authors = get_phillies_articles()
    
    # Distribute across 5 columns
    num_per_column = 4
    filtered_titles1b = merged_titles[:num_per_column]
    filtered_titles2b = merged_titles[num_per_column:num_per_column*2]
    filtered_titles3b = merged_titles[num_per_column*2:num_per_column*3]
    filtered_titles4b = merged_titles[num_per_column*3:num_per_column*4]
    filtered_titles5b = merged_titles[num_per_column*4:num_per_column*5] if len(merged_titles) > num_per_column*4 else []
    
    filtered_urls1b = merged_urls[:num_per_column]
    filtered_urls2b = merged_urls[num_per_column:num_per_column*2]
    filtered_urls3b = merged_urls[num_per_column*2:num_per_column*3]
    filtered_urls4b = merged_urls[num_per_column*3:num_per_column*4]
    filtered_urls5b = merged_urls[num_per_column*4:num_per_column*5] if len(merged_urls) > num_per_column*4 else []
    
    filtered_images1b = merged_images[:num_per_column]
    filtered_images2b = merged_images[num_per_column:num_per_column*2]
    filtered_images3b = merged_images[num_per_column*2:num_per_column*3]
    filtered_images4b = merged_images[num_per_column*3:num_per_column*4]
    filtered_images5b = merged_images[num_per_column*4:num_per_column*5] if len(merged_images) > num_per_column*4 else []
    
    filtered_blurbs1b = merged_blurbs[:num_per_column]
    filtered_blurbs2b = merged_blurbs[num_per_column:num_per_column*2]
    filtered_blurbs3b = merged_blurbs[num_per_column*2:num_per_column*3]
    filtered_blurbs4b = merged_blurbs[num_per_column*3:num_per_column*4]
    filtered_blurbs5b = merged_blurbs[num_per_column*4:num_per_column*5] if len(merged_blurbs) > num_per_column*4 else []
    
    filtered_authors1b = merged_authors[:num_per_column]
    filtered_authors2b = merged_authors[num_per_column:num_per_column*2]
    filtered_authors3b = merged_authors[num_per_column*2:num_per_column*3]
    filtered_authors4b = merged_authors[num_per_column*3:num_per_column*4]
    filtered_authors5b = merged_authors[num_per_column*4:num_per_column*5] if len(merged_authors) > num_per_column*4 else []

    dict1 = create_dict(filtered_titles1b, filtered_urls1b)
    dict2 = create_dict(filtered_titles2b, filtered_urls2b)
    dict3 = create_dict(filtered_titles3b, filtered_urls3b)
    dict4 = create_dict(filtered_titles4b, filtered_urls4b)
    dict5 = create_dict(filtered_titles5b, filtered_urls5b)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}

    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    shuffled_dict = dict(combined_list)
    keys2 = list(shuffled_dict.keys())
    values2 = list(shuffled_dict.values())

    video_id = phillies_request()
    
    # Use the safe embed code function to handle None or invalid videos
    embed_code2 = create_safe_embed_code(video_id, 'Philadelphia Phillies')

    # Read the contents of the template file into a string
    with open('templates/index3a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html3 = template.render(zip2=zip, column1b=filtered_titles1b, column2b=filtered_titles2b, column3b=filtered_titles3b, column4b=filtered_titles4b, column5b=filtered_titles5b, urls1b=filtered_urls1b, urls2b=filtered_urls2b, urls3b=filtered_urls3b, urls4b=filtered_urls4b, urls5b=filtered_urls5b, imageURLS1b=filtered_images1b,imageURLS2b=filtered_images2b, imageURLS3b=filtered_images3b, imageURLS4b=filtered_images4b, imageURLS5b=filtered_images5b, keys2=keys2, values2=values2, embed_code2=embed_code2, blurbs1b=filtered_blurbs1b, blurbs2b=filtered_blurbs2b, blurbs3b=filtered_blurbs3b, blurbs4b=filtered_blurbs4b, blurbs5b=filtered_blurbs5b, authors1b=filtered_authors1b, authors2b=filtered_authors2b, authors3b=filtered_authors3b, authors4b=filtered_authors4b, authors5b=filtered_authors5b)

    return html3

@cache.cached(timeout=3600, key_prefix='flyers_articles')
def get_flyers_articles():
    """
    Get Flyers articles with caching. Fetches on demand from all sources.
    """
    article_sources = collect_articles_for_team("flyers")
    if not article_sources:
        return [], [], [], [], []
    merged = merge_articles_from_sources(article_sources)
    titles, urls, images, blurbs, authors = merged
    if titles and urls:
        titles, urls, images, blurbs, authors = enhance_article_data(
            titles, urls, images, blurbs, authors, max_enhance=10, enhance_all=True
        )
    return titles, urls, images, blurbs, authors

@app.route('/flyers')
def flyers():
    # Get cached articles (or fetch if cache miss)
    merged_titles, merged_urls, merged_images, merged_blurbs, merged_authors = get_flyers_articles()
    
    # Distribute across 5 columns
    num_per_column = 4
    filtered_titles1c = merged_titles[:num_per_column]
    filtered_titles2c = merged_titles[num_per_column:num_per_column*2]
    filtered_titles3c = merged_titles[num_per_column*2:num_per_column*3]
    filtered_titles4c = merged_titles[num_per_column*3:num_per_column*4]
    filtered_titles5c = merged_titles[num_per_column*4:num_per_column*5] if len(merged_titles) > num_per_column*4 else []
    
    filtered_urls1c = merged_urls[:num_per_column]
    filtered_urls2c = merged_urls[num_per_column:num_per_column*2]
    filtered_urls3c = merged_urls[num_per_column*2:num_per_column*3]
    filtered_urls4c = merged_urls[num_per_column*3:num_per_column*4]
    filtered_urls5c = merged_urls[num_per_column*4:num_per_column*5] if len(merged_urls) > num_per_column*4 else []
    
    filtered_images1c = merged_images[:num_per_column]
    filtered_images2c = merged_images[num_per_column:num_per_column*2]
    filtered_images3c = merged_images[num_per_column*2:num_per_column*3]
    filtered_images4c = merged_images[num_per_column*3:num_per_column*4]
    filtered_images5c = merged_images[num_per_column*4:num_per_column*5] if len(merged_images) > num_per_column*4 else []
    
    filtered_blurbs1c = merged_blurbs[:num_per_column]
    filtered_blurbs2c = merged_blurbs[num_per_column:num_per_column*2]
    filtered_blurbs3c = merged_blurbs[num_per_column*2:num_per_column*3]
    filtered_blurbs4c = merged_blurbs[num_per_column*3:num_per_column*4]
    filtered_blurbs5c = merged_blurbs[num_per_column*4:num_per_column*5] if len(merged_blurbs) > num_per_column*4 else []
    
    filtered_authors1c = merged_authors[:num_per_column]
    filtered_authors2c = merged_authors[num_per_column:num_per_column*2]
    filtered_authors3c = merged_authors[num_per_column*2:num_per_column*3]
    filtered_authors4c = merged_authors[num_per_column*3:num_per_column*4]
    filtered_authors5c = merged_authors[num_per_column*4:num_per_column*5] if len(merged_authors) > num_per_column*4 else []

    dict1 = create_dict(filtered_titles1c, filtered_urls1c)
    dict2 = create_dict(filtered_titles2c, filtered_urls2c)
    dict3 = create_dict(filtered_titles3c, filtered_urls3c)
    dict4 = create_dict(filtered_titles4c, filtered_urls4c)
    dict5 = create_dict(filtered_titles5c, filtered_urls5c)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}

    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    shuffled_dict = dict(combined_list)
    keys3 = list(shuffled_dict.keys())
    values3 = list(shuffled_dict.values())

    video_id = flyers_request()
    
    # Use the safe embed code function to handle None or invalid videos
    embed_code3 = create_safe_embed_code(video_id, 'Philadelphia Flyers')

    # Read the contents of the template file into a string
    with open('templates/index4a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html4 = template.render(zip3=zip, column1c=filtered_titles1c, column2c=filtered_titles2c, column3c=filtered_titles3c, column4c=filtered_titles4c, column5c=filtered_titles5c, urls1c=filtered_urls1c, urls2c=filtered_urls2c, urls3c=filtered_urls3c, urls4c=filtered_urls4c, urls5c=filtered_urls5c, imageURLS1c=filtered_images1c,imageURLS2c=filtered_images2c, imageURLS3c=filtered_images3c, imageURLS4c=filtered_images4c, imageURLS5c=filtered_images5c, keys3=keys3, values3=values3, embed_code3=embed_code3, blurbs1c=filtered_blurbs1c, blurbs2c=filtered_blurbs2c, blurbs3c=filtered_blurbs3c, blurbs4c=filtered_blurbs4c, blurbs5c=filtered_blurbs5c, authors1c=filtered_authors1c, authors2c=filtered_authors2c, authors3c=filtered_authors3c, authors4c=filtered_authors4c, authors5c=filtered_authors5c)

    return html4

if __name__ == '__main__':
    app.run()
