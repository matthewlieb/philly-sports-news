"""Collect, de-duplicate and rank articles for a team from all scraped sources."""
from typing import List

from scrapers.source_collectors import collect_articles_for_team
from utils.article_filter import get_source_name_from_url, merge_and_rank_articles


def collect_ranked_articles(team: str, max_articles: int = 20) -> List[dict]:
    """Articles as dicts with title, url, image, description, author, source, team."""
    articles = []
    seen = set()
    for src in collect_articles_for_team(team):
        titles = src.get("titles", [])
        urls = src.get("urls", [])
        images = src.get("images", [])
        blurbs = src.get("blurbs", [])
        authors = src.get("authors", [])
        for i, url in enumerate(urls):
            url = (url or "").strip()
            if not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            source = get_source_name_from_url(url)
            author = (authors[i] if i < len(authors) else "") or ""
            author = author.removeprefix("-- ").strip()
            if author in ("", "Unknown", "None"):
                author = source
            articles.append({
                "title": (titles[i] if i < len(titles) else "").strip(),
                "url": url,
                "image": images[i] if i < len(images) else None,
                "description": (blurbs[i] if i < len(blurbs) else "").strip(),
                "author": author,
                "source": source,
                "team": team,
            })
    return merge_and_rank_articles(articles, max_articles=max_articles)
