"""
SB Nation scraper for Liberty Ballers, Bleeding Green Nation, The Good Phight, and Broad Street Hockey.

SB Nation sites use a consistent structure with entry boxes, making them ideal for
a unified scraper that can handle multiple team sites.
"""

from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from articleEnhancer import enhance_article_data


class SBNationScraper(BaseScraper):
    """
    Scraper for SB Nation websites (libertyballers.com, bleedinggreennation.com, etc.).
    
    These sites use a consistent structure with 'c-entry-box--compact' classes,
    making them ideal for a unified scraping approach.
    """
    
    # CSS selectors to try in order of preference
    ARTICLE_SELECTORS = [
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
    
    # Selectors for finding article titles
    TITLE_SELECTORS = ["h2", "h3", "h1", "a", ".title", "[class*='title']"]
    
    # Selectors for finding article blurbs/descriptions
    BLURB_SELECTORS = [
        "p.c-entry-box--compact__body",
        "div.c-entry-box--compact__body",
        "p.excerpt",
        "div.excerpt",
        "p.summary",
        "div.summary",
        "p"
    ]
    
    # Selectors for finding author information
    AUTHOR_SELECTORS = ["span", ".author", "[class*='author']", "[class*='byline']"]
    
    def __init__(self, base_url: str, source_name: str):
        """
        Initialize SB Nation scraper.
        
        Args:
            base_url: Base URL of the SB Nation site (e.g., 'https://www.libertyballers.com')
            source_name: Human-readable source name (e.g., 'Liberty Ballers')
        """
        super().__init__(base_url, source_name)
    
    def _extract_article_data(self, article_element) -> Optional[Tuple[str, str, str, str, str]]:
        """
        Extract article data from a single article element.
        
        Args:
            article_element: BeautifulSoup element containing article data
            
        Returns:
            Tuple of (title, url, image_url, description, author) or None if invalid
        """
        # Extract title
        title = self.extract_text(
            self.find_element(article_element, self.TITLE_SELECTORS)
        )
        
        # Extract URL - check if element itself is a link
        link_element = None
        if article_element.name == 'a' and article_element.get('href'):
            link_element = article_element
        else:
            link_element = article_element.find("a", href=True)
        
        url = ""
        if link_element and link_element.get('href'):
            url = self.normalize_url(link_element['href'])
        
        # Only process if we have either a title or a valid URL
        if not title and not url:
            return None
        
        # Extract image
        img_element = article_element.find("img")
        image_url = None
        if img_element and img_element.get('src'):
            img_src = img_element['src']
            image_url = self.normalize_url(img_src)
        
        # Extract description/blurb
        description = self.extract_text(
            self.find_element(article_element, self.BLURB_SELECTORS)
        )
        # Limit description length
        if len(description) > 300:
            description = description[:300] + "..."
        
        # Extract author
        author_element = self.find_element(article_element, self.AUTHOR_SELECTORS)
        author = self.extract_text(author_element, "-- None")
        if author != "-- None":
            author = f"-- {author}"
        
        return (title, url, image_url or "", description, author)
    
    def _find_article_links(self, soup: BeautifulSoup) -> List:
        """
        Fallback method to find article links when standard selectors fail.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of article link elements
        """
        # Try to find article links with specific classes
        article_links = soup.find_all(
            'a', 
            href=True, 
            class_=lambda x: x and ('entry' in str(x).lower() or 'title' in str(x).lower())
        )
        
        if article_links:
            return article_links[:15]  # Limit to 15 links
        
        # Fallback: find any links that look like articles
        all_links = soup.find_all('a', href=True)
        article_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = self.extract_text(link)
            
            # Check if link looks like an article
            is_article_link = (
                ('/20' in href or '/news' in href or '/article' in href or 
                 '/2024' in href or '/2025' in href) and
                len(text) > 20 and
                not any(ad_word in text.lower() for ad_word in [
                    'advertisement', 'sponsored', 'promoted', 
                    'subscribe', 'newsletter', 'sign up'
                ])
            )
            
            if is_article_link:
                article_links.append(link)
        
        return article_links[:15]
    
    def scrape(self, url: str) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
        """
        Scrape articles from the given URL.
        
        Args:
            url: URL to scrape articles from
            
        Returns:
            Tuple of (titles, urls, images, descriptions, authors) lists
        """
        soup = self.fetch_page(url)
        if not soup:
            print(f"Failed to fetch page: {url}")
            return [], [], [], [], []
        
        # Try to find articles using standard selectors
        article_elements = self.find_elements(soup, self.ARTICLE_SELECTORS)
        
        # If no articles found, try fallback method
        if not article_elements:
            print(f"No articles found with standard selectors, trying fallback method...")
            article_links = self._find_article_links(soup)
            # Convert links to elements for processing
            article_elements = []
            for link in article_links:
                parent = link.find_parent(['article', 'div', 'li'])
                article_elements.append(parent if parent else link)
        
        if not article_elements:
            print(f"No articles found on {url}")
            return [], [], [], [], []
        
        print(f"Found {len(article_elements)} articles using selector")
        
        # Extract data from each article
        titles = []
        urls = []
        images = []
        descriptions = []
        authors = []
        
        for element in article_elements:
            article_data = self._extract_article_data(element)
            if article_data:
                title, url, image, description, author = article_data
                titles.append(title)
                urls.append(url)
                images.append(image)
                descriptions.append(description)
                authors.append(author)
        
        print(f"Successfully scraped {len(titles)} articles from {url}")
        
        # Enhance articles with missing data
        if titles and urls:
            titles, urls, images, descriptions, authors = enhance_article_data(
                titles, urls, images, descriptions, authors, max_enhance=5
            )
        
        return titles, urls, images, descriptions, authors

