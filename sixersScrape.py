import requests
from bs4 import BeautifulSoup
from articleEnhancer import enhance_article_data

def scrape_website(URL):
    try:
        page = requests.get(URL)
        page.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return [], [], [], []

    soup = BeautifulSoup(page.content, "html.parser")

    # Try multiple selectors for different website structures
    selectors_to_try = [
        "li.ContentGrid_contentGridColumnQuarter__Uiwvc",
        "li[class*='ContentGrid']",
        "li[class*='content']",
        "article",
        "div[class*='article']",
        "div[class*='story']",
        "div[class*='post']"
    ]
    
    results = []
    for selector in selectors_to_try:
        results = soup.select(selector)
        if len(results) > 0:
            print(f"Found {len(results)} articles using selector: {selector}")
            break
    
    # If no articles found, try to find any links that look like articles
    if len(results) == 0:
        links = soup.find_all('a', href=True)
        article_links = []
        for link in links:
            href = link.get('href', '')
            text = link.get_text().strip()
            # Look for links that might be articles
            if (('/news' in href or '/article' in href or '/story' in href) and 
                len(text) > 20 and 
                not any(ad_word in text.lower() for ad_word in ['advertisement', 'sponsored', 'promoted'])):
                article_links.append(link)
        
        if len(article_links) > 0:
            print(f"Found {len(article_links)} potential article links")
            # Convert links to div-like structure for processing
            results = [link.parent for link in article_links[:10] if link.parent]

    titles = []
    urls = []
    blurbs = []
    imageURLS = []
    authors = []

    print(f"Processing {len(results)} articles.")
    for entry in results:
        # Try to find title in various ways
        title_element = None
        for title_selector in ["h3", "h2", "h1", "a", ".title", "[class*='title']"]:
            title_element = entry.find(title_selector)
            if title_element and title_element.get_text().strip():
                break
        
        if title_element:
            title_text = title_element.get_text().strip()
            if title_text and len(title_text) > 5:
                titles.append(title_text)
                print(f"Found title: {title_text}")
            else:
                titles.append("")
                print("No valid title found.")
        else:
            titles.append("")
            print("No title found.")

        # Try to find blurb
        blurb_element = None
        for blurb_selector in ["p", "div", ".excerpt", "[class*='excerpt']", "[class*='description']"]:
            blurb_element = entry.find(blurb_selector)
            if blurb_element and blurb_element.get_text().strip():
                break
        
        if blurb_element:
            blurb_text = blurb_element.get_text().strip()
            if blurb_text and len(blurb_text) > 10:
                blurbs.append(blurb_text)
                print(f"Found blurb: {blurb_text}")
            else:
                blurbs.append("")
                print("No valid blurb found.")
        else:
            blurbs.append("")
            print("No blurb found.")

        # Try to find URL
        link_element = None
        for link_selector in ["a", "[href]"]:
            link_element = entry.find(link_selector)
            if link_element and link_element.get('href'):
                break
        
        if link_element and link_element.get('href'):
            href = link_element['href']
            if href.startswith('/'):
                full_url = f"https://www.nba.com{href}"
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"https://www.nba.com/{href}"
            urls.append(full_url)
            print(f"Found URL: {full_url}")
        else:
            urls.append("")
            print("No URL found.")

        # Try to find image
        image_element = None
        for image_selector in ["img", "[src]"]:
            image_element = entry.find(image_selector)
            if image_element and image_element.get("src"):
                break
        
        if image_element and image_element.get("src"):
            imageURL = image_element["src"]
            if imageURL.startswith('http'):
                imageURLS.append(imageURL)
                print(f"Found image URL: {imageURL}")
            else:
                imageURLS.append("")
                print("No valid image URL found.")
        else:
            imageURLS.append("")
            print("No image found.")
        
        # Add author (Sixers site doesn't show authors, so use default)
        authors.append("-- Philadelphia 76ers")

    return titles, urls, imageURLS, blurbs, authors

URL = "https://www.nba.com/sixers/archives"
titles2a, urls2a, imageURLS2a, blurbs2a, authors2a = scrape_website(URL)

# Enhance all articles to ensure complete data for every card
if titles2a and urls2a:
    print("Enhancing Sixers articles with complete data...")
    titles2a, urls2a, imageURLS2a, blurbs2a, authors2a = enhance_article_data(
        titles2a, urls2a, imageURLS2a, blurbs2a, authors2a, max_enhance=10, enhance_all=True
    )

# Print out the first few items for testing
for i in range(min(6, len(titles2a))):  # Ensuring not to go out of index
    print("Title:", titles2a[i])
    print("Blurb:", blurbs2a[i])
    print("URL:", urls2a[i])
    print("Image URL:", imageURLS2a[i], "\n")
