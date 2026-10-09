import os
import random
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, Response, abort, redirect, render_template, request, url_for  # noqa: E402
from flask_caching import Cache  # noqa: E402

import lib.config as config  # noqa: E402
from lib import briefs as brief_store  # noqa: E402
from lib import store  # noqa: E402
from lib.article_enhancer import enhance_article_data  # noqa: E402
from lib.articles import collect_ranked_articles  # noqa: E402
from lib.teams import SITE_NAME, SITE_URL, TEAM_SLUGS, TEAMS, X_HANDLE, brief_path  # noqa: E402
from lib.youtube_utils import create_safe_embed_code, get_embeddable_video_id  # noqa: E402

app = Flask(__name__)

_redis_url = os.environ.get("REDIS_URL")
app.config["CACHE_TYPE"] = "redis" if _redis_url else "simple"
app.config["CACHE_REDIS_URL"] = _redis_url
app.config["CACHE_DEFAULT_TIMEOUT"] = 3600
cache = Cache(app)

ADSENSE_CLIENT = "ca-pub-5735663043216445"
_BOT_MARKERS = ("bot", "crawl", "spider", "slurp", "preview", "monitor", "curl", "python", "headless")


@app.context_processor
def _site_globals():
    return {
        "site_name": SITE_NAME,
        "site_url": SITE_URL,
        "teams": TEAMS,
        "x_handle": X_HANDLE,
        "adsense_client": ADSENSE_CLIENT,
        "ga_id": os.environ.get("GA_MEASUREMENT_ID"),
        "site_verification": os.environ.get("GOOGLE_SITE_VERIFICATION"),
        "year": date.today().year,
    }


@app.after_request
def _count_pageview(response):
    """Daily per-path view counts in Redis, skipping bots, so traffic is measurable without third parties."""
    if (request.method == "GET" and response.status_code == 200 and response.mimetype == "text/html"):
        ua = (request.user_agent.string or "").lower()
        if ua and not any(m in ua for m in _BOT_MARKERS):
            try:
                k = store.key("views", brief_store.local_today(), request.path)
                r = store.client()
                r.incr(k)
                r.expire(k, 400 * 86400)
            except Exception as e:
                app.logger.warning("pageview count failed: %s", e)
    return response


@cache.memoize(timeout=3600)
def get_team_articles(team):
    articles = collect_ranked_articles(team, max_articles=20)
    if not articles:
        return []
    cols = [[a[k] for a in articles] for k in ("title", "url", "image", "description", "author")]
    titles, urls, images, blurbs, authors = enhance_article_data(*cols, max_enhance=5, enhance_all=False)
    for a, t, im, b in zip(articles, titles, images, blurbs):
        a["title"], a["image"], a["description"] = t, im, b
    return [a for a in articles if a["title"]]


@cache.memoize(timeout=3600)
def get_team_video(team):
    if not config.api_key:
        return None
    return get_embeddable_video_id(team, config.api_key)


def render_team(team):
    articles = get_team_articles(team)
    ticker = random.sample(articles[:10], k=min(5, len(articles)))
    return render_template(
        "team.html",
        team=TEAMS[team],
        articles=articles,
        ticker=ticker,
        embed_code=create_safe_embed_code(get_team_video(team), TEAMS[team]["full_name"]),
        brief=brief_store.latest_brief(team),
        canonical=SITE_URL + TEAMS[team]["path"],
    )


@app.route("/")
def home():
    return render_team("eagles")


@app.route("/eagles")
def eagles_alias():
    return redirect("/", code=301)


@app.route("/<team>")
def team_page(team):
    if team not in TEAMS or team == "eagles":
        abort(404)
    return render_team(team)


@app.route("/<team>/brief/<day>")
def brief_page(team, day):
    if team not in TEAMS:
        abort(404)
    brief = brief_store.get_brief(team, day)
    if not brief:
        abort(404)
    dates = brief_store.brief_dates(team)
    i = dates.index(day) if day in dates else -1
    newer = dates[i - 1] if i > 0 else None
    older = dates[i + 1] if 0 <= i < len(dates) - 1 else None
    others = [(t, brief_store.get_brief(t, day)) for t in TEAM_SLUGS if t != team]
    return render_template(
        "brief.html",
        team=TEAMS[team],
        brief=brief,
        newer=newer,
        older=older,
        others=[(t, b) for t, b in others if b],
        canonical=SITE_URL + brief_path(team, day),
    )


@app.route("/briefs")
@app.route("/<team>/briefs")
def briefs_archive(team=None):
    if team is not None and team not in TEAMS:
        abort(404)
    if team:
        entries = [(team, d) for d in brief_store.brief_dates(team, limit=60)]
    else:
        entries = brief_store.recent_briefs(limit=60)
    items = [b for b in (brief_store.get_brief(t, d) for t, d in entries) if b]
    return render_template(
        "briefs.html",
        team=TEAMS.get(team),
        items=items,
        canonical=SITE_URL + (url_for("briefs_archive", team=team) if team else "/briefs"),
    )


@app.route("/about")
def about():
    return render_template("about.html", canonical=SITE_URL + "/about")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", canonical=SITE_URL + "/privacy")


@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /health\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@app.route("/ads.txt")
def ads_txt():
    pub = ADSENSE_CLIENT.removeprefix("ca-")
    return Response(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", mimetype="text/plain")


@app.route("/googlefc317b0f2c8dfa8c.html")
def search_console_verification():
    return Response("google-site-verification: googlefc317b0f2c8dfa8c.html", mimetype="text/html")


@app.route("/sitemap.xml")
def sitemap():
    today = brief_store.local_today()
    urls = [(SITE_URL + TEAMS[t]["path"], today, "hourly") for t in TEAM_SLUGS]
    urls += [(SITE_URL + "/briefs", today, "daily")]
    urls += [(SITE_URL + f"/{t}/briefs", today, "daily") for t in TEAM_SLUGS]
    urls += [(SITE_URL + brief_path(t, d), d, "never") for t, d in brief_store.recent_briefs(limit=2000)]
    urls += [(SITE_URL + "/about", None, "yearly"), (SITE_URL + "/privacy", None, "yearly")]
    return Response(render_template("sitemap.xml", urls=urls), mimetype="application/xml")


@app.route("/health")
def health():
    return "ok", 200


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run()
