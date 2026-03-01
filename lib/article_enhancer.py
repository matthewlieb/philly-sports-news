"""
Utility functions to enhance article data by fetching missing information
from individual article pages using Open Graph meta tags and article content
"""

import requests
from bs4 import BeautifulSoup
import time

def fetch_article_metadata(url, timeout=10):
    """
    Fetch missing article metadata from an article URL
    Returns: (title, image_url, description, author) or (None, None, None, None) if failed
    """
    if not url or not url.startswith('http'):
        return None, None, None, None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Try to get Open Graph meta tags first (most reliable)
        og_title = soup.find("meta", property="og:title")
        og_image = soup.find("meta", property="og:image")
        og_description = soup.find("meta", property="og:description")

        # Fallback to standard meta tags
        meta_title = soup.find("meta", attrs={"name": "title"}) or soup.find("title")
        meta_description = soup.find("meta", attrs={"name": "description"})

        # Extract title
        title = None
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
        elif meta_title:
            if hasattr(meta_title, 'get'):
                title = meta_title.get('content', '').strip()
            else:
                title = meta_title.get_text().strip()

        # Extract image
        image_url = None
        if og_image and og_image.get('content'):
            image_url = og_image['content'].strip()
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
        else:
            featured_img = soup.find("img", class_=lambda x: x and ('featured' in str(x).lower() or 'hero' in str(x).lower()))
            if featured_img and featured_img.get('src'):
                image_url = featured_img['src']
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"

        # Extract description
        description = None
        if og_description and og_description.get('content'):
            description = og_description['content'].strip()
        elif meta_description and meta_description.get('content'):
            description = meta_description['content'].strip()
        else:
            article_content = soup.find("article") or soup.find("div", class_=lambda x: x and ('article' in str(x).lower() or 'content' in str(x).lower()))
            if article_content:
                first_p = article_content.find("p")
                if first_p:
                    description = first_p.get_text().strip()[:200]

        # Extract author
        author = None
        author_meta = soup.find("meta", property="article:author") or soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get('content'):
            author = author_meta['content'].strip()
        else:
            author_elem = soup.find("span", class_=lambda x: x and 'author' in str(x).lower()) or \
                         soup.find("a", class_=lambda x: x and 'author' in str(x).lower()) or \
                         soup.find("div", class_=lambda x: x and 'author' in str(x).lower())
            if author_elem:
                author = author_elem.get_text().strip()

        return title, image_url, description, author

    except Exception as e:
        print(f"Error fetching metadata from {url}: {e}")
        return None, None, None, None

def enhance_article_data(titles, urls, imageURLS, blurbs, authors=None, max_enhance=10, enhance_all=False):
    """
    Enhance article data by fetching information from individual article pages.
    Returns tuple of (titles, urls, images, blurbs, authors).
    """
    if not urls or len(urls) == 0:
        return titles, urls, imageURLS, blurbs, authors

    enhanced_titles = list(titles) if titles else []
    enhanced_urls = list(urls) if urls else []
    enhanced_images = list(imageURLS) if imageURLS else []
    enhanced_blurbs = list(blurbs) if blurbs else []
    enhanced_authors = list(authors) if authors else []

    max_len = max(len(enhanced_titles), len(enhanced_urls), len(enhanced_images), len(enhanced_blurbs))
    while len(enhanced_titles) < max_len:
        enhanced_titles.append("")
    while len(enhanced_urls) < max_len:
        enhanced_urls.append("")
    while len(enhanced_images) < max_len:
        enhanced_images.append(None)
    while len(enhanced_blurbs) < max_len:
        enhanced_blurbs.append("")
    if authors:
        while len(enhanced_authors) < max_len:
            enhanced_authors.append("")

    enhanced_count = 0
    articles_to_process = min(max_len, max_enhance)

    for i in range(articles_to_process):
        url = enhanced_urls[i] if i < len(enhanced_urls) else None
        if not url or not url.startswith('http'):
            continue

        if enhance_all:
            should_enhance = True
        else:
            needs_title = not enhanced_titles[i] or enhanced_titles[i].strip() == ""
            needs_image = not enhanced_images[i] or enhanced_images[i] == None or str(enhanced_images[i]).strip() == ""
            needs_blurb = not enhanced_blurbs[i] or enhanced_blurbs[i].strip() == ""
            needs_author = authors and (not enhanced_authors[i] or enhanced_authors[i].strip() == "")
            should_enhance = needs_title or needs_image or needs_blurb or needs_author

        if should_enhance:
            print(f"Enhancing article {i+1}/{articles_to_process}: {url[:80]}...")
            title, image_url, description, author = fetch_article_metadata(url)

            if enhance_all:
                if title:
                    enhanced_titles[i] = title
                if image_url:
                    enhanced_images[i] = image_url
                if description:
                    enhanced_blurbs[i] = description
                if author:
                    enhanced_authors[i] = "-- " + author
            else:
                if title and (not enhanced_titles[i] or enhanced_titles[i].strip() == ""):
                    enhanced_titles[i] = title
                if image_url and (not enhanced_images[i] or enhanced_images[i] == None or str(enhanced_images[i]).strip() == ""):
                    enhanced_images[i] = image_url
                if description and (not enhanced_blurbs[i] or enhanced_blurbs[i].strip() == ""):
                    enhanced_blurbs[i] = description
                if author and authors and (not enhanced_authors[i] or enhanced_authors[i].strip() == ""):
                    enhanced_authors[i] = "-- " + author

            enhanced_count += 1
            if i < articles_to_process - 1:
                time.sleep(0.3)

    print(f"Enhanced {enhanced_count} articles with complete data")
    return enhanced_titles, enhanced_urls, enhanced_images, enhanced_blurbs, enhanced_authors
