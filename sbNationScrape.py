import requests 
from bs4 import BeautifulSoup
from articleEnhancer import enhance_article_data
from scrapers.rss_scraper import fetch_rss_feed, rss_to_article_lists

def scrape_website(URL):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        page = requests.get(URL, headers=headers, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
        
        # Try multiple selectors for different website structures
        # For SB Nation sites (libertyballers, bleedinggreennation, etc.)
        selectors_to_try = [
            "div.c-entry-box--compact__body",
            "article.c-entry-box--compact",
            "div.c-entry-box--compact",
            "article",
            "div[class*='entry-box']",
            "div[class*='entry']",
            "div[class*='article']",
            "div[class*='post']:not([class*='ad'])",
            "div[class*='story']",
            "div[class*='item']"
        ]
        
        results = []
        for selector in selectors_to_try:
            results = soup.select(selector)
            if len(results) > 0:
                print(f"Found {len(results)} articles using selector: {selector}")
                break
        
        # If no articles found, try to find article links directly
        if len(results) == 0:
            # Look for article links with titles
            article_links = soup.find_all('a', href=True, class_=lambda x: x and ('entry' in str(x).lower() or 'title' in str(x).lower()))
            if not article_links:
                # Fallback: find any links that look like articles
                links = soup.find_all('a', href=True)
                article_links = []
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    # Look for links that might be articles (contain year, have substantial text)
                    if (('/20' in href or '/news' in href or '/article' in href or '/2024' in href or '/2025' in href) and 
                        len(text) > 20 and 
                        not any(ad_word in text.lower() for ad_word in ['advertisement', 'sponsored', 'promoted', 'subscribe', 'newsletter'])):
                        article_links.append(link)
            
            if len(article_links) > 0:
                print(f"Found {len(article_links)} potential article links")
                # Use the links themselves or their parent containers
                results = []
                for link in article_links[:15]:  # Get more links to work with
                    # Try to find a parent container
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent:
                        results.append(parent)
                    else:
                        # Create a wrapper div with the link
                        results.append(link)

        titles = []
        urls = []
        authors = []
        imageURLS = []
        blurbs = []

        for result in results:
            # Try to find title in various ways
            title_element = None
            for title_selector in ["h2", "h3", "h1", "a", ".title", "[class*='title']"]:
                title_element = result.find(title_selector)
                if title_element and title_element.get_text().strip():
                    break
            
            # Extract title - try multiple methods
            title_text = None
            if title_element:
                title_text = title_element.get_text().strip()
            else:
                # If no title element found, try getting text from the result itself
                title_text = result.get_text().strip()[:200]  # Limit to 200 chars
            
            # Try to find link - check if result itself is a link
            link = None
            if result.name == 'a' and result.get('href'):
                link = result
            else:
                link = result.find("a", href=True) or title_element
            
            # Extract URL
            link_url = None
            if link and link.get('href'):
                link_url = link['href']
                if not link_url.startswith('http'):
                    # Try to determine base URL from the original URL
                    from urllib.parse import urlparse
                    parsed = urlparse(URL)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    if link_url.startswith('/'):
                        link_url = base_url + link_url
                    else:
                        link_url = base_url + '/' + link_url
            
            # Only process if we have either a title or a valid URL
            if (title_text and len(title_text) > 5) or link_url:
                if title_text and len(title_text) > 5:
                    titles.append(title_text)
                else:
                    titles.append("")  # Will be filled by enhancer
                
                if link_url:
                    urls.append(link_url)
                else:
                    urls.append("")
                
                # Extract image
                img_tag = result.find("img")
                if img_tag and img_tag.get('src'):
                    img_src = img_tag['src']
                    if img_src.startswith('http'):
                        imageURLS.append(img_src)
                    elif img_src.startswith('//'):
                        imageURLS.append('https:' + img_src)
                    else:
                        # Use base URL from original URL
                        from urllib.parse import urlparse
                        parsed = urlparse(URL)
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                        if img_src.startswith('/'):
                            imageURLS.append(base_url + img_src)
                        else:
                            imageURLS.append(base_url + '/' + img_src)
                else:
                    imageURLS.append(None)
                
                # Try to find blurb/excerpt
                blurb = None
                # Try multiple selectors for blurbs
                blurb_selectors = [
                    "p.c-entry-box--compact__body",
                    "div.c-entry-box--compact__body",
                    "p.excerpt",
                    "div.excerpt",
                    "p.summary",
                    "div.summary",
                    "p"
                ]
                for blurb_selector in blurb_selectors:
                    blurb = result.select_one(blurb_selector)
                    if blurb and blurb.get_text().strip():
                        break
                
                if blurb:
                    blurbs.append(blurb.get_text().strip()[:300])  # Limit to 300 chars
                else:
                    blurbs.append("")
                
                # Try to find author
                author = None
                for author_selector in ["span", ".author", "[class*='author']", "[class*='byline']"]:
                    author = result.find(author_selector)
                    if author and author.get_text().strip():
                        break
                
                # Add author
                if author is None:
                    authors.append("-- None")
                else:
                    authors.append("-- " + author.get_text().strip())

        print(f"Successfully scraped {len(titles)} articles from {URL}")
        return titles, urls, authors, imageURLS, blurbs
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred scraping {URL}: {e}")
        return [], [], [], [], []
    except Exception as e:
        print(f"Unexpected error scraping {URL}: {e}")
        return [], [], [], [], []

URL1 = "https://www.bleedinggreennation.com/"
URL2 = "https://www.libertyballers.com/"
URL3 = "https://www.thegoodphight.com/"
URL4 = "https://www.broadstreethockey.com/"

# Try RSS feeds first for all SB Nation sites (more reliable)
# Use fallback URLs if primary RSS feed doesn't work
from scrapers.rss_scraper import fetch_rss_feed_with_fallback, RSS_FEEDS

print("Fetching articles from RSS feeds...")

# Liberty Ballers (Sixers)
print("Fetching Liberty Ballers articles from RSS feed...")
rss_articles = fetch_rss_feed_with_fallback(RSS_FEEDS['liberty_ballers'], max_articles=20)
if rss_articles and len(rss_articles) > 0:
    titles1a, urls1a, imageURLS1a, blurbs1a, authors1a = rss_to_article_lists(rss_articles)
    print(f"✅ Successfully fetched {len(titles1a)} articles from Liberty Ballers RSS feed")
else:
    print("RSS feed failed, falling back to scraping...")
    titles1a, urls1a, authors1a, imageURLS1a, blurbs1a = scrape_website(URL2)

# Bleeding Green Nation (Eagles)
print("Fetching Bleeding Green Nation articles from RSS feed...")
rss_articles = fetch_rss_feed_with_fallback(RSS_FEEDS['bleeding_green_nation'], max_articles=20)
if rss_articles and len(rss_articles) > 0:
    titles1, urls1, imageURLS1, blurbs1, authors1 = rss_to_article_lists(rss_articles)
    print(f"✅ Successfully fetched {len(titles1)} articles from Bleeding Green Nation RSS feed")
else:
    print("RSS feed failed, falling back to scraping...")
    titles1, urls1, authors1, imageURLS1, blurbs1 = scrape_website(URL1)

# The Good Phight (Phillies)
print("Fetching The Good Phight articles from RSS feed...")
rss_articles = fetch_rss_feed_with_fallback(RSS_FEEDS['the_good_phight'], max_articles=20)
if rss_articles and len(rss_articles) > 0:
    titles1b, urls1b, imageURLS1b, blurbs1b, authors1b = rss_to_article_lists(rss_articles)
    print(f"✅ Successfully fetched {len(titles1b)} articles from The Good Phight RSS feed")
else:
    print("RSS feed failed, falling back to scraping...")
    titles1b, urls1b, authors1b, imageURLS1b, blurbs1b = scrape_website(URL3)

# Broad Street Hockey (Flyers) - This one works!
print("Fetching Broad Street Hockey articles from RSS feed...")
rss_articles = fetch_rss_feed_with_fallback(RSS_FEEDS['broad_street_hockey'], max_articles=20)
if rss_articles and len(rss_articles) > 0:
    titles1c, urls1c, imageURLS1c, blurbs1c, authors1c = rss_to_article_lists(rss_articles)
    print(f"✅ Successfully fetched {len(titles1c)} articles from Broad Street Hockey RSS feed")
else:
    print("RSS feed failed, falling back to scraping...")
    titles1c, urls1c, authors1c, imageURLS1c, blurbs1c = scrape_website(URL4)

# Enhance ALL articles to ensure complete data for every card
# This fetches full article metadata from individual pages to populate all fields
print("Enhancing all articles with complete data from individual pages...")
titles1, urls1, imageURLS1, blurbs1, authors1 = enhance_article_data(titles1, urls1, imageURLS1, blurbs1, authors1, max_enhance=10, enhance_all=True)
titles1a, urls1a, imageURLS1a, blurbs1a, authors1a = enhance_article_data(titles1a, urls1a, imageURLS1a, blurbs1a, authors1a, max_enhance=10, enhance_all=True)
titles1b, urls1b, imageURLS1b, blurbs1b, authors1b = enhance_article_data(titles1b, urls1b, imageURLS1b, blurbs1b, authors1b, max_enhance=10, enhance_all=True)
titles1c, urls1c, imageURLS1c, blurbs1c, authors1c = enhance_article_data(titles1c, urls1c, imageURLS1c, blurbs1c, authors1c, max_enhance=10, enhance_all=True)

# You can then use the lists as needed. For example, you could print out the first item in each list like this:
# print(titles1[0])
# print(titles1a[0])



