"""
Advanced article filtering and quality scoring system.

This module provides functions to filter articles based on completeness
and quality, ensuring only fully populated articles are displayed.
"""

from typing import List, Tuple, Optional
from urllib.parse import urlparse


def calculate_article_quality_score(title: str, url: str, image: Optional[str], 
                                   description: str, author: Optional[str] = None) -> int:
    """
    Calculate a quality score for an article based on completeness.
    
    Scoring system:
    - Title: 30 points (required)
    - URL: 30 points (required)
    - Image: 25 points (highly preferred)
    - Description: 15 points (preferred)
    - Author: 5 points (nice to have)
    
    Maximum score: 105 points
    
    Args:
        title: Article title
        url: Article URL
        image: Article image URL (optional)
        description: Article description/blurb (optional)
        author: Article author (optional)
        
    Returns:
        Quality score (0-105)
    """
    score = 0
    
    # Title is required (30 points)
    if title and title.strip() and len(title.strip()) > 5:
        score += 30
    else:
        return 0  # No title = invalid article
    
    # URL is required (30 points)
    if url and url.strip() and url.startswith('http'):
        score += 30
    else:
        return 0  # No valid URL = invalid article
    
    # Image is highly preferred (25 points)
    if image and image.strip() and image != "None" and not image.startswith('/None'):
        # Check if it's a valid image URL
        if image.startswith('http') or image.startswith('//'):
            score += 25
        elif image.startswith('/'):
            score += 20  # Relative URL, but still valid
    
    # Description is preferred (15 points)
    if description and description.strip() and len(description.strip()) > 20:
        score += 15
    elif description and description.strip():
        score += 10  # Short description
    
    # Author is nice to have (5 points)
    if author and author.strip() and author != "-- None":
        score += 5
    
    return score


def is_article_complete(title: str, url: str, image: Optional[str], 
                       description: str, min_score: int = 70) -> bool:
    """
    Check if an article has all required fields and meets minimum quality.
    
    Args:
        title: Article title
        url: Article URL
        image: Article image URL
        description: Article description
        min_score: Minimum quality score required (default: 70)
        
    Returns:
        True if article is complete and meets quality threshold
    """
    score = calculate_article_quality_score(title, url, image, description)
    return score >= min_score


def filter_complete_articles(titles: List[str], urls: List[str], 
                            images: List[Optional[str]], 
                            descriptions: List[str],
                            authors: Optional[List[str]] = None,
                            min_score: int = 70) -> Tuple[List[str], List[str], 
                                                          List[Optional[str]], 
                                                          List[str], 
                                                          Optional[List[str]]]:
    """
    Filter articles to only include those that are complete and meet quality standards.
    
    Args:
        titles: List of article titles
        urls: List of article URLs
        images: List of article image URLs
        descriptions: List of article descriptions
        authors: Optional list of authors
        min_score: Minimum quality score (default: 70)
        
    Returns:
        Filtered lists of (titles, urls, images, descriptions, authors)
    """
    filtered_titles = []
    filtered_urls = []
    filtered_images = []
    filtered_descriptions = []
    filtered_authors = [] if authors else None
    
    # Ensure all lists are the same length
    max_len = max(len(titles), len(urls), len(images), len(descriptions))
    if authors:
        max_len = max(max_len, len(authors))
    
    # Pad shorter lists
    titles = list(titles) + [""] * (max_len - len(titles))
    urls = list(urls) + [""] * (max_len - len(urls))
    images = list(images) + [None] * (max_len - len(images))
    descriptions = list(descriptions) + [""] * (max_len - len(descriptions))
    if authors:
        authors = list(authors) + [""] * (max_len - len(authors))
    
    for i in range(max_len):
        title = titles[i] if i < len(titles) else ""
        url = urls[i] if i < len(urls) else ""
        image = images[i] if i < len(images) else None
        description = descriptions[i] if i < len(descriptions) else ""
        author = authors[i] if authors and i < len(authors) else None
        
        # Check if article is complete
        if is_article_complete(title, url, image, description, min_score):
            filtered_titles.append(title)
            filtered_urls.append(url)
            filtered_images.append(image)
            filtered_descriptions.append(description)
            if filtered_authors is not None:
                filtered_authors.append(author if author else "-- Unknown")
    
    return filtered_titles, filtered_urls, filtered_images, filtered_descriptions, filtered_authors


def get_source_name_from_url(url: str) -> str:
    """
    Extract a readable source name from a URL.
    
    Args:
        url: Article URL
        
    Returns:
        Source name (e.g., "Liberty Ballers" from libertyballers.com)
    """
    if not url or not url.startswith('http'):
        return "Unknown Source"
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Extract site name (before first dot)
        site_name = domain.split('.')[0]
        
        # Convert to title case and handle common cases
        source_mapping = {
            'libertyballers': 'Liberty Ballers',
            'bleedinggreennation': 'Bleeding Green Nation',
            'thegoodphight': 'The Good Phight',
            'broadstreethockey': 'Broad Street Hockey',
            'philadelphiaeagles': 'Philadelphia Eagles',
            'nbcsports': 'NBC Sports Philadelphia',
            'phillyvoice': 'PhillyVoice',
            'insidetheiggles': 'Inside the Iggles',
            'thesixersense': 'The Sixer Sense',
            'thatballsouttahere': 'That Balls Outta Here',
            'broadstreetbuzz': 'Broad Street Buzz',
            'mlb': 'MLB.com',
            'nba': 'NBA.com',
            'nhl': 'NHL.com'
        }
        
        return source_mapping.get(site_name.lower(), site_name.title())
    except Exception:
        return "Unknown Source"


def merge_and_rank_articles(all_articles: List[dict], max_articles: int = 20) -> List[dict]:
    """
    Merge articles from multiple sources and rank by quality.
    
    Args:
        all_articles: List of article dicts with keys: title, url, image, description, author, source
        max_articles: Maximum number of articles to return
        
    Returns:
        Sorted list of articles by quality score (highest first)
    """
    # Calculate scores for all articles
    scored_articles = []
    for article in all_articles:
        score = calculate_article_quality_score(
            article.get('title', ''),
            article.get('url', ''),
            article.get('image'),
            article.get('description', ''),
            article.get('author')
        )
        article['quality_score'] = score
        scored_articles.append(article)
    
    # Sort by quality score (descending)
    scored_articles.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    
    # Return top articles
    return scored_articles[:max_articles]

