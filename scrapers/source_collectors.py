"""
On-demand article collection per team. Each source returns (titles, urls, images, blurbs, authors).
Used by app.get_*_articles() so scraping runs when the cache misses, not at import time.
"""

from typing import List, Tuple, Optional
from bs4 import BeautifulSoup

from scrapers.fetcher import get_html
from scrapers.rss_scraper import fetch_rss_feed_with_fallback, rss_to_article_lists, RSS_FEEDS


def _normalize(*lists) -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """Ensure we always return exactly 5 lists of equal length."""
    titles, urls, images, blurbs, authors = lists
    n = max(len(titles), len(urls), len(images or []), len(blurbs), len(authors or []))
    def pad(lst, default):
        return list(lst) + [default] * (n - len(lst)) if lst else [default] * n
    return (
        pad(titles, ""),
        pad(urls, ""),
        pad(images, None),
        pad(blurbs, ""),
        pad(authors, "-- Unknown"),
    )


def _first_text(el, default=""):
    if el is None:
        return default
    t = el.get_text(strip=True) if hasattr(el, "get_text") else str(el).strip()
    return t or default


def _first_attr(el, attr, default=None):
    if el is None:
        return default
    v = el.get(attr) if hasattr(el, "get") else None
    return v or default


# ---- RSS-based (SB Nation) ----

def collect_sb_nation_bleeding_green() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """Bleeding Green Nation (Eagles)."""
    articles = fetch_rss_feed_with_fallback(RSS_FEEDS["bleeding_green_nation"], max_articles=20)
    if articles:
        return _normalize(*rss_to_article_lists(articles))
    return _normalize([], [], [], [], [])


def collect_sb_nation_liberty_ballers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """Liberty Ballers (Sixers)."""
    articles = fetch_rss_feed_with_fallback(RSS_FEEDS["liberty_ballers"], max_articles=20)
    if articles:
        return _normalize(*rss_to_article_lists(articles))
    return _normalize([], [], [], [], [])


def collect_sb_nation_the_good_phight() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """The Good Phight (Phillies)."""
    articles = fetch_rss_feed_with_fallback(RSS_FEEDS["the_good_phight"], max_articles=20)
    if articles:
        return _normalize(*rss_to_article_lists(articles))
    return _normalize([], [], [], [], [])


def collect_sb_nation_broad_street_hockey() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """Broad Street Hockey (Flyers)."""
    articles = fetch_rss_feed_with_fallback(RSS_FEEDS["broad_street_hockey"], max_articles=20)
    if articles:
        return _normalize(*rss_to_article_lists(articles))
    return _normalize([], [], [], [], [])


# ---- Official team sites (with resilient selectors) ----

def collect_eagles_official() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """Philadelphia Eagles official site."""
    url = "https://www.philadelphiaeagles.com/news/all"
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in ["div.d3-l-col__col-3", "article", "div[class*='story']", "li[class*='card']"]:
        results = soup.select(selector)
        if not results:
            continue
        for entry in results:
            title_el = entry.find("h3") or entry.find("h2") or entry.find("h1")
            title = _first_text(title_el)
            if not title or len(title) < 5:
                continue
            a = entry.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            link = href if href.startswith("http") else "https://www.philadelphiaeagles.com" + href
            img = entry.find("img")
            src = _first_attr(img, "src") or _first_attr(img, "data-src")
            if src and "/t_lazy" in str(src):
                src = str(src).replace("/t_lazy", "")
            if src and not src.startswith("http"):
                src = "https://www.philadelphiaeagles.com" + src if src.startswith("/") else None
            titles.append(title)
            urls.append(link)
            images.append(src)
            blurbs.append(_first_text(entry.find("p") or entry.find("div"))[:300])
            authors.append("-- Philadelphia Eagles")
        if titles:
            break
    return _normalize(titles, urls, images, blurbs, authors)


def collect_phillies_mlb() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """MLB Phillies news."""
    url = "https://www.mlb.com/phillies/news"
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in ["article.article-item", "article", "div[class*='article']", "li[class*='card']"]:
        results = soup.select(selector)
        if not results:
            continue
        for entry in results:
            title_el = entry.find("h1", class_="article-item__headline") or entry.find("h2") or entry.find("h3") or entry.find("h1")
            title = _first_text(title_el)
            if not title or len(title) < 5:
                continue
            a = entry.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            link = href if href.startswith("http") else "https://www.mlb.com" + href
            img = entry.find("img", class_="lazyload") or entry.find("img")
            src = _first_attr(img, "data-srcset") or _first_attr(img, "data-src") or _first_attr(img, "src")
            if src and isinstance(src, str):
                src = src.split(",")[0].strip().split()[0] if " " in src else src
            if src and not src.startswith("http"):
                src = "https://www.mlb.com" + src if src.startswith("/") else None
            titles.append(title)
            urls.append(link)
            images.append(src)
            blurbs.append(_first_text(entry.find("p", class_="article-item__contributor-date") or entry.find("p"))[:300])
            authors.append("-- Philadelphia Phillies")
        if titles:
            break
    return _normalize(titles, urls, images, blurbs, authors)


def collect_flyers_nhl() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """NHL Flyers news."""
    url = "https://www.nhl.com/flyers/news"
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in [
        "article.nhl-c-card",
        "article[class*='card']",
        "article",
        "div[class*='card']",
        "li[class*='article']",
    ]:
        results = soup.select(selector)
        if not results:
            continue
        for entry in results:
            title_el = entry.find("h3", class_="fa-text__title") or entry.find("h3") or entry.find("h2")
            title = _first_text(title_el)
            if not title or len(title) < 5:
                continue
            parent_a = entry.find_parent("a")
            a = parent_a or entry.find("a", href=True)
            if not a or not a.get("href"):
                continue
            href = a["href"]
            link = href if href.startswith("http") else "https://www.nhl.com" + href
            img = entry.find("img")
            src = _first_attr(img, "src")
            if src and not src.startswith("http"):
                src = "https://www.nhl.com" + src if src.startswith("/") else None
            titles.append(title)
            urls.append(link)
            images.append(src)
            blurbs.append("")
            authors.append("-- Philadelphia Flyers")
        if titles:
            break
    return _normalize(titles, urls, images, blurbs, authors)


def collect_sixers_nba() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    """NBA Sixers news."""
    url = "https://www.nba.com/sixers/archives"
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in [
        "li.ContentGrid_contentGridColumnQuarter__Uiwvc",
        "li[class*='ContentGrid']",
        "li[class*='content']",
        "article",
        "div[class*='article']",
        "div[class*='story']",
        "a[href*='/news']",
        "a[href*='/story']",
    ]:
        results = soup.select(selector)
        if not results:
            continue
        for entry in results:
            if entry.name == "a":
                title = _first_text(entry)
                href = entry.get("href", "")
            else:
                title_el = entry.find("h3") or entry.find("h2") or entry.find("h1") or entry.find("a")
                title = _first_text(title_el)
                a = entry.find("a", href=True)
                href = a["href"] if a else ""
            if not title or len(title) < 10:
                continue
            if not href:
                continue
            link = href if href.startswith("http") else "https://www.nba.com" + (href if href.startswith("/") else "/" + href)
            img = entry.find("img") if hasattr(entry, "find") else None
            src = _first_attr(img, "src") if img else None
            if src and not src.startswith("http"):
                src = "https://www.nba.com" + src if src.startswith("/") else None
            titles.append(title[:200])
            urls.append(link)
            images.append(src)
            blurbs.append(_first_text(entry.find("p") or entry.find("div"))[:300] if hasattr(entry, "find") else "")
            authors.append("-- Philadelphia 76ers")
        if titles:
            break
    return _normalize(titles, urls, images, blurbs, authors)


# ---- NBC Sports Philadelphia ----

def _collect_nbc(url: str, default_author: str) -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in ["li.story-card.story-card__list-item", "li.story-card", "article", "div[class*='story-card']"]:
        results = soup.select(selector)
        if not results:
            continue
        for item in results:
            title_tag = item.find("h3", class_="story-card__title") or item.find("h3") or item.find("h2")
            if not title_tag:
                continue
            a_tag = title_tag.find("a") or item.find("a", href=True)
            if not a_tag or not a_tag.get("href"):
                continue
            title = _first_text(a_tag) or _first_text(title_tag)
            if not title:
                continue
            url_val = a_tag["href"]
            if not url_val.startswith("http"):
                url_val = "https://www.nbcsports.com" + url_val
            img_wrap = item.find("div", class_="imagewrap2") or item.find("div", class_="imagewrap") or item.find("div", class_=lambda c: c and "image" in str(c).lower())
            img = item.find("img") if not img_wrap else (img_wrap.find("img") or item.find("img"))
            src = _first_attr(img, "src") if img else None
            if src and not src.startswith("http"):
                src = "https://www.nbcsports.com" + src
            excerpt = item.find("div", class_="story-card__excerpt") or item.find("p")
            blurb = _first_text(excerpt) if excerpt else ""
            titles.append(title)
            urls.append(url_val)
            images.append(src)
            blurbs.append(blurb[:300])
            authors.append(default_author)
        if titles:
            break
    return _normalize(titles, urls, images, blurbs, authors)


def collect_nbc_eagles() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_nbc("https://www.nbcsports.com/philadelphia/eagles", "-- NBC Sports Philadelphia")


def collect_nbc_sixers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_nbc("https://www.nbcsports.com/philadelphia/sixers", "-- NBC Sports Philadelphia")


def collect_nbc_phillies() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_nbc("https://www.nbcsports.com/philadelphia/phillies", "-- NBC Sports Philadelphia")


def collect_nbc_flyers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_nbc("https://www.nbcsports.com/philadelphia/flyers", "-- NBC Sports Philadelphia")


# ---- PhillyVoice ----

def _collect_phillyvoice(url: str) -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in ["div.article-text", "article", "div[class*='article']"]:
        results = soup.select(selector)
        if not results:
            continue
        for entry in results:
            h1 = entry.find("h1")
            links = entry.find_all("a", href=True)
            if not h1 or len(links) < 2:
                continue
            title = _first_text(h1)
            link_url = links[1].get("href", "")
            if not title or not link_url:
                continue
            full_url = link_url if link_url.startswith("http") else "https://www.phillyvoice.com" + link_url
            titles.append(title)
            urls.append(full_url)
            images.append(None)
            blurbs.append("")
            authors.append("-- PhillyVoice")
        if titles:
            break
    for i, url_val in enumerate(urls[:15]):
        if i >= len(blurbs):
            break
        try:
            import requests
            r = requests.get(url_val, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}, timeout=8)
            if r.status_code != 200:
                continue
            s = BeautifulSoup(r.content, "html.parser")
            body = s.find("div", class_="body-content")
            if body and body.find("p"):
                blurbs[i] = _first_text(body.find("p"))[:300]
            # Image: try og:image first (reliable), then feature-image, then first article img
            img_url = None
            og_img = s.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                img_url = og_img["content"].strip()
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
            if not img_url:
                feat = s.find("div", class_="feature-image")
                if feat:
                    img_el = feat.find("img")
                    if img_el:
                        img_url = img_el.get("src") or img_el.get("data-src")
                if not img_url:
                    article_el = s.find("article") or s.find("div", class_=lambda c: c and "article" in str(c).lower())
                    if article_el:
                        first_img = article_el.find("img", src=True)
                        if first_img:
                            img_url = first_img.get("src") or first_img.get("data-src")
            if img_url and not img_url.startswith("http"):
                img_url = "https://www.phillyvoice.com" + img_url if img_url.startswith("/") else None
            if img_url:
                images[i] = img_url
            byline = s.find("span", class_="author-name") or s.find("a", class_="author-name")
            if byline:
                authors[i] = "-- " + _first_text(byline)
        except Exception:
            pass
    return _normalize(titles, urls, images, blurbs, authors)


def collect_phillyvoice_eagles() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_phillyvoice("https://www.phillyvoice.com/tags/eagles/")


def collect_phillyvoice_sixers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_phillyvoice("https://www.phillyvoice.com/tags/sixers/")


def collect_phillyvoice_phillies() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_phillyvoice("https://www.phillyvoice.com/tags/phillies/")


def collect_phillyvoice_flyers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_phillyvoice("https://www.phillyvoice.com/tags/flyers/")


# ---- FanSided ----

def _collect_fansided(url: str, default_author: str) -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    html = get_html(url)
    if not html:
        return _normalize([], [], [], [], [])
    soup = BeautifulSoup(html, "html.parser")
    titles, urls, images, blurbs, authors = [], [], [], [], []
    for selector in ["a.articleLink_1iblg8d", "a[class*='articleLink']", "a[class*='article']", "article a"]:
        results = soup.select(selector)
        if not results:
            continue
        for a in results[:15]:
            href = a.get("href")
            title = a.get("title") or _first_text(a)
            if not href or not title or len(title) < 10:
                continue
            titles.append(title)
            urls.append(href)
            images.append(None)
            blurbs.append("")
            authors.append(default_author)
        if titles:
            break
    for i in range(min(5, len(urls))):
        try:
            import requests
            r = requests.get(urls[i], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}, timeout=8)
            if r.status_code != 200:
                continue
            s = BeautifulSoup(r.content, "html.parser")
            og_img = s.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                images[i] = og_img["content"]
            og_desc = s.find("meta", property="og:description") or s.find("meta", attrs={"name": "description"})
            if og_desc and og_desc.get("content"):
                blurbs[i] = og_desc["content"][:300]
            byline = s.find("span", class_=lambda c: c and "byline" in str(c).lower()) or s.find("a", class_=lambda c: c and "author" in str(c).lower())
            if byline:
                authors[i] = "-- " + _first_text(byline)
        except Exception:
            pass
    return _normalize(titles, urls, images, blurbs, authors)


def collect_fansided_eagles() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_fansided("https://insidetheiggles.com/philadelphia-eagles-news/", "-- FanSided")


def collect_fansided_sixers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_fansided("https://thesixersense.com/philadelphia-76ers-news/", "-- FanSided")


def collect_fansided_phillies() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_fansided("https://thatballsouttahere.com/philadelphia-phillies-news/", "-- FanSided")


def collect_fansided_flyers() -> Tuple[List[str], List[str], List[Optional[str]], List[str], List[str]]:
    return _collect_fansided("https://broadstreetbuzz.com/philadelphia-flyers-news/", "-- FanSided")


# ---- Team source lists ----

SOURCES_EAGLES = [
    collect_sb_nation_bleeding_green,
    collect_eagles_official,
    collect_nbc_eagles,
    collect_phillyvoice_eagles,
    collect_fansided_eagles,
]

SOURCES_SIXERS = [
    collect_sb_nation_liberty_ballers,
    collect_sixers_nba,
    collect_nbc_sixers,
    collect_phillyvoice_sixers,
    collect_fansided_sixers,
]

SOURCES_PHILLIES = [
    collect_sb_nation_the_good_phight,
    collect_phillies_mlb,
    collect_nbc_phillies,
    collect_phillyvoice_phillies,
    collect_fansided_phillies,
]

SOURCES_FLYERS = [
    collect_sb_nation_broad_street_hockey,
    collect_flyers_nhl,
    collect_nbc_flyers,
    collect_phillyvoice_flyers,
    collect_fansided_flyers,
]


def collect_articles_for_team(team: str) -> List[dict]:
    """
    Run all sources for a team and return a list of source dicts for merge_articles_from_sources.
    """
    if team == "eagles":
        sources = SOURCES_EAGLES
    elif team == "sixers":
        sources = SOURCES_SIXERS
    elif team == "phillies":
        sources = SOURCES_PHILLIES
    elif team == "flyers":
        sources = SOURCES_FLYERS
    else:
        return []

    out = []
    for fn in sources:
        try:
            titles, urls, images, blurbs, authors = fn()
            if titles and urls:
                out.append({
                    "titles": titles,
                    "urls": urls,
                    "images": images or [None] * len(titles),
                    "blurbs": blurbs,
                    "authors": authors or ["-- Unknown"] * len(titles),
                })
        except Exception as e:
            print(f"Source {fn.__name__} failed: {e}")
            continue
    return out
