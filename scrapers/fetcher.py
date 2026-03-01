"""
Unified HTML fetcher: requests first, optional Selenium fallback for JS-heavy pages.

Set USE_SELENIUM=1 in the environment to enable Selenium fallback when requests
returns empty or fails. On Heroku, add Chrome buildpacks for Selenium.
"""

import os
from typing import Optional

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_html_requests(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch page HTML with requests. Returns None on failure."""
    try:
        import requests
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Requests fetch failed for {url[:60]}...: {e}")
        return None


def get_html_selenium(url: str, timeout: int = 20) -> Optional[str]:
    """Fetch page HTML using headless Chrome. Returns None on failure or if Selenium unavailable."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        print("Selenium not installed. Install with: pip install selenium")
        return None

    driver = None
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"user-agent={DEFAULT_HEADERS['User-Agent']}")

        # Heroku sets this when using Chrome buildpack
        chrome_bin = os.environ.get("GOOGLE_CHROME_SHIM")
        if chrome_bin:
            options.binary_location = chrome_bin

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located(("tag_name", "body")))
        html = driver.page_source
        return html
    except Exception as e:
        print(f"Selenium fetch failed for {url[:60]}...: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def get_html(url: str, use_selenium_fallback: Optional[bool] = None, min_length: int = 500) -> Optional[str]:
    """
    Fetch page HTML. Tries requests first; if USE_SELENIUM=1 and response is empty/short, tries Selenium.

    Args:
        url: Page URL
        use_selenium_fallback: If True, try Selenium when requests fails or returns short content.
                               If None, reads USE_SELENIUM env var (1 = True).
        min_length: If requests returns HTML shorter than this, treat as failure and try Selenium (when enabled).

    Returns:
        HTML string or None
    """
    html = get_html_requests(url)
    if html and len(html) >= min_length:
        return html

    if use_selenium_fallback is None:
        use_selenium_fallback = os.environ.get("USE_SELENIUM", "").strip() == "1"
    if use_selenium_fallback and (not html or len(html) < min_length):
        html = get_html_selenium(url)
    return html if html else None
