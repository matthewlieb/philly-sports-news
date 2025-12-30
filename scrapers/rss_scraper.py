"""
RSS Feed scraper for news sources that provide RSS feeds.

RSS feeds are more reliable than web scraping as they provide structured data
and are less likely to break when websites change their HTML structure.
"""

import feedparser
from typing import List, Tuple, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import time


def fetch_rss_feed(feed_url: str, max_articles: int = 20) -> List[dict]:
    """
    Fetch and parse an RSS feed.
    
    Args:
        feed_url: URL of the RSS feed
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries with keys: title, url, image, description, author, source
    """
    try:
        feed = feedparser.parse(feed_url)
        
        # Check for parsing errors
        if feed.bozo:
            error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Unknown error"
            print(f"⚠️  RSS feed parsing error for {feed_url}: {error_msg}")
            # Still try to use entries if available despite bozo flag
            if not feed.entries:
                return []
        elif not feed.entries:
            print(f"⚠️  RSS feed {feed_url} returned no entries")
            return []
        
        articles = []
        
        for entry in feed.entries[:max_articles]:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                continue
            
            # Extract URL
            url = entry.get('link', '').strip()
            if not url:
                continue
            
            # Extract description
            description = ""
            if 'summary' in entry:
                description = entry.summary.strip()
            elif 'description' in entry:
                description = entry.description.strip()
            
            # Clean HTML from description
            if description:
                soup = BeautifulSoup(description, "html.parser")
                description = soup.get_text().strip()
                # Limit description length
                if len(description) > 300:
                    description = description[:300] + "..."
            
            # Extract image from media_content or media_thumbnail
            image_url = None
            if 'media_content' in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get('url')
            elif 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                image_url = entry.media_thumbnail[0].get('url')
            elif 'image' in entry:
                image_url = entry.image.get('href')
            elif 'links' in entry:
                # Look for image links
                for link in entry.links:
                    if link.get('type', '').startswith('image/'):
                        image_url = link.get('href')
                        break
            
            # If no image in feed, try to fetch from article page
            if not image_url:
                image_url = _fetch_image_from_article(url)
            
            # Extract author
            author = None
            if 'author' in entry:
                author = entry.author.strip()
            elif 'author_detail' in entry:
                author = entry.author_detail.get('name', '').strip()
            
            # Extract source name from feed
            source = feed.feed.get('title', 'Unknown Source')
            if not source or source == 'Unknown Source':
                # Try to get from URL
                parsed = urlparse(url)
                domain = parsed.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                source = domain.split('.')[0].title()
            
            article = {
                'title': title,
                'url': url,
                'image': image_url,
                'description': description,
                'author': f"-- {author}" if author else None,
                'source': source
            }
            
            articles.append(article)
        
        print(f"Successfully fetched {len(articles)} articles from RSS feed: {feed_url}")
        return articles
        
    except Exception as e:
        print(f"Error fetching RSS feed {feed_url}: {e}")
        return []


def _fetch_image_from_article(url: str, timeout: int = 5) -> Optional[str]:
    """
    Fetch image from article page using Open Graph meta tags.
    
    Args:
        url: Article URL
        timeout: Request timeout in seconds
        
    Returns:
        Image URL or None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Try Open Graph image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get('content'):
            return og_image['content'].strip()
        
        # Try to find featured image
        featured_img = soup.find("img", class_=lambda x: x and ('featured' in str(x).lower() or 'hero' in str(x).lower()))
        if featured_img and featured_img.get('src'):
            img_src = featured_img['src']
            if img_src.startswith('//'):
                return f"https:{img_src}"
            elif img_src.startswith('/'):
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}{img_src}"
            elif img_src.startswith('http'):
                return img_src
        
        return None
        
    except Exception as e:
        # Silently fail - image fetching is optional
        return None


def rss_to_article_lists(articles: List[dict]) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """
    Convert RSS article dictionaries to the standard list format.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Tuple of (titles, urls, images, descriptions, authors) lists
    """
    titles = []
    urls = []
    images = []
    descriptions = []
    authors = []
    
    for article in articles:
        titles.append(article.get('title', ''))
        urls.append(article.get('url', ''))
        images.append(article.get('image'))
        descriptions.append(article.get('description', ''))
        authors.append(article.get('author') or article.get('source', 'Unknown'))
    
    return titles, urls, images, descriptions, authors


# RSS Feed URLs for Philadelphia sports sources
# Try multiple URLs in order of preference
RSS_FEEDS = {
    'liberty_ballers': [
        'https://www.libertyballers.com/rss/current',
        'https://www.libertyballers.com/feed',
        'https://www.libertyballers.com/rss',
    ],
    'bleeding_green_nation': [
        'https://www.bleedinggreennation.com/rss/current',
        'https://www.bleedinggreennation.com/feed',
        'https://www.bleedinggreennation.com/rss',
    ],
    'the_good_phight': [
        'https://www.thegoodphight.com/rss/current',
        'https://www.thegoodphight.com/feed',
        'https://www.thegoodphight.com/rss',
    ],
    'broad_street_hockey': [
        'https://www.broadstreethockey.com/rss/current',
        'https://www.broadstreethockey.com/feed',
        'https://www.broadstreethockey.com/rss',
    ],
}


def fetch_rss_feed_with_fallback(feed_urls: List[str], max_articles: int = 20) -> List[dict]:
    """
    Try multiple RSS feed URLs until one works.
    
    Args:
        feed_urls: List of RSS feed URLs to try in order
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    for url in feed_urls:
        articles = fetch_rss_feed(url, max_articles)
        if articles and len(articles) > 0:
            print(f"✅ Successfully fetched {len(articles)} articles from {url}")
            return articles
        else:
            print(f"⚠️  No articles from {url}, trying next URL...")
    
    return []

