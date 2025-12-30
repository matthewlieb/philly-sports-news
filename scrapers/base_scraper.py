"""
Base scraper class providing common functionality for all news scrapers.

This module defines an abstract base class that all specific scrapers should inherit from,
ensuring consistent structure, error handling, and data extraction patterns across the codebase.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import time


class BaseScraper(ABC):
    """
    Abstract base class for all news scrapers.
    
    Provides common functionality for:
    - HTTP requests with proper headers and error handling
    - HTML parsing with BeautifulSoup
    - URL normalization
    - Consistent data structure (title, url, image, description, author)
    
    All scrapers should inherit from this class and implement the scrape() method.
    """
    
    # Default headers to mimic a real browser request
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 10
    
    def __init__(self, base_url: str, source_name: str):
        """
        Initialize the scraper with base URL and source name.
        
        Args:
            base_url: The base URL of the news source (e.g., 'https://www.libertyballers.com')
            source_name: Human-readable name of the source (e.g., 'Liberty Ballers')
        """
        self.base_url = base_url.rstrip('/')
        self.source_name = source_name
        self._session = None
    
    def _get_session(self) -> requests.Session:
        """
        Get or create a requests session for connection pooling.
        
        Returns:
            A requests.Session object for making HTTP requests
        """
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.DEFAULT_HEADERS)
        return self._session
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch a web page and return a BeautifulSoup object.
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object if successful, None otherwise
            
        Raises:
            requests.RequestException: If the HTTP request fails
        """
        try:
            session = self._get_session()
            response = session.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def normalize_url(self, url: str, base_url: Optional[str] = None) -> str:
        """
        Normalize a URL to ensure it's absolute and properly formatted.
        
        Args:
            url: The URL to normalize (may be relative or absolute)
            base_url: Base URL to use if url is relative (defaults to self.base_url)
            
        Returns:
            A normalized absolute URL
        """
        if not url:
            return ""
        
        base = base_url or self.base_url
        
        # Already absolute URL
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        # Protocol-relative URL
        if url.startswith('//'):
            return f"https:{url}"
        
        # Absolute path
        if url.startswith('/'):
            return f"{base}{url}"
        
        # Relative path
        return urljoin(base, url)
    
    def extract_text(self, element, default: str = "") -> str:
        """
        Safely extract text from a BeautifulSoup element.
        
        Args:
            element: BeautifulSoup element to extract text from
            default: Default value if element is None or has no text
            
        Returns:
            Extracted text, stripped of whitespace, or default value
        """
        if element is None:
            return default
        text = element.get_text(strip=True)
        return text if text else default
    
    def find_element(self, soup: BeautifulSoup, selectors: List[str]) -> Optional:
        """
        Try multiple CSS selectors to find an element.
        
        Args:
            soup: BeautifulSoup object to search in
            selectors: List of CSS selectors to try in order
            
        Returns:
            First matching element found, or None if none match
        """
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element
        return None
    
    def find_elements(self, soup: BeautifulSoup, selectors: List[str]) -> List:
        """
        Try multiple CSS selectors to find elements.
        
        Args:
            soup: BeautifulSoup object to search in
            selectors: List of CSS selectors to try in order
            
        Returns:
            First non-empty list of matching elements found, or empty list
        """
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                return elements
        return []
    
    @abstractmethod
    def scrape(self, url: str) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
        """
        Scrape articles from a given URL.
        
        This method must be implemented by each specific scraper.
        
        Args:
            url: The URL to scrape articles from
            
        Returns:
            Tuple of (titles, urls, images, descriptions, authors) lists
            All lists should have the same length
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of the scraper."""
        return f"{self.__class__.__name__}(base_url='{self.base_url}', source='{self.source_name}')"

