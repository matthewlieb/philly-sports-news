import os
import random
from datetime import date

from dotenv import load_dotenv

load_dotenv()

import json  # noqa: E402
import secrets  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, session, url_for  # noqa: E402

import lib.config as config  # noqa: E402
from lib import briefs as brief_store  # noqa: E402
from lib import newsletter  # noqa: E402
from lib.creators import CREATORS  # noqa: E402
from lib import store  # noqa: E402
from lib.article_enhancer import enhance_article_data  # noqa: E402
from lib.articles import collect_ranked_articles  # noqa: E402
from lib.teams import SITE_NAME, SITE_URL, TEAM_SLUGS, TEAMS, X_HANDLE, brief_path  # noqa: E402
from lib.youtube_utils import create_safe_embed_code, get_embeddable_video_id  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SECURE=bool(os.environ.get("SECRET_KEY")), SESSION_COOKIE_SAMESITE="Strict",
                  SESSION_COOKIE_HTTPONLY=True)

ADSENSE_CLIENT = "ca-pub-5735663043216445"
_BOT_MARKERS = ("bot", "crawl", "spider", "slurp", "preview", "monitor", "curl", "python", "headless",
                "externalhit", "externalagent")  # Facebook/Meta link-preview fetchers


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
        "newsletter_on": newsletter.enabled(),
        "creators": CREATORS,
    }


@app.after_request
def _count_pageview(response):
    """Daily per-path view counts in Redis, skipping bots, so traffic is measurable without third parties."""
    if (request.method == "GET" and response.status_code == 200 and response.mimetype == "text/html"):
        ua = (request.user_agent.string or "").lower()
        if ua and not any(m in ua for m in _BOT_MARKERS):
            threading.Thread(target=_record_view, args=(request.path,), daemon=True).start()
    return response


def _record_view(path: str) -> None:
    try:
        k = store.key("views", brief_store.local_today(), path)
        r = store.client()
        if hasattr(r, "pipeline"):
            r.pipeline().incr(k).expire(k, 400 * 86400).execute()
        else:
            r.incr(k)
            r.expire(k, 400 * 86400)
    except Exception as e:
        app.logger.warning("pageview count failed: %s", e)


_local: dict[str, tuple[float, object]] = {}


def _memo(name: str, fn, ttl: int = 60):
    """Keep a value in this process for ttl seconds. Redis is a cross-country round trip (~100ms) away,
    and page data only changes a few times an hour."""
    hit = _local.get(name)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    value = fn()
    _local[name] = (time.time(), value)
    return value


_refreshing: set[str] = set()
_refresh_lock = threading.Lock()


def _stale_while_revalidate(name: str, fn, max_age: int = 3600):
    """Serve the last stored result instantly and rebuild it in the background once it is older than max_age.

    Rebuilding a team page means scraping every news source (~20s), so no visitor should ever wait for it;
    only the very first build of a key (nothing stored yet) happens inline.
    """
    r, k = store.client(), store.key("page", name)
    raw = r.get(k)

    def rebuild():
        try:
            value = fn()
            r.set(k, json.dumps({"at": time.time(), "value": value}))
            return value
        finally:
            with _refresh_lock:
                _refreshing.discard(k)

    if raw is None:
        with _refresh_lock:
            _refreshing.add(k)
        return rebuild()
    cached = json.loads(raw)
    if time.time() - cached["at"] > max_age:
        with _refresh_lock:
            start = k not in _refreshing
            _refreshing.add(k)
        if start:
            threading.Thread(target=rebuild, daemon=True).start()
    return cached["value"]


def _build_team_articles(team):
    articles = collect_ranked_articles(team, max_articles=20)
    if not articles:
        return []
    cols = [[a[k] for a in articles] for k in ("title", "url", "image", "description", "author")]
    titles, urls, images, blurbs, authors = enhance_article_data(*cols, max_enhance=5, enhance_all=False)
    for a, t, im, b in zip(articles, titles, images, blurbs):
        a["title"], a["image"], a["description"] = t, im, b
    return [a for a in articles if a["title"]]


def get_team_articles(team):
    return _memo(f"articles:{team}", lambda: _stale_while_revalidate(f"articles:{team}", lambda: _build_team_articles(team)))


def get_team_video(team):
    if not config.api_key:
        return None
    return _memo(f"video:{team}", lambda: _stale_while_revalidate(
        f"video:{team}", lambda: get_embeddable_video_id(team, config.api_key)))


def render_team(team):
    articles = get_team_articles(team)
    ticker = random.sample(articles[:10], k=min(5, len(articles)))
    return render_template(
        "team.html",
        team=TEAMS[team],
        articles=articles,
        ticker=ticker,
        embed_code=create_safe_embed_code(get_team_video(team), TEAMS[team]["full_name"]),
        brief=_memo(f"latest_brief:{team}", lambda: brief_store.latest_brief(team)),
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
    others = [t for t in TEAM_SLUGS if t != team]
    brief, *other_briefs = brief_store.get_briefs([(team, day)] + [(t, day) for t in others])
    if not brief:
        abort(404)
    dates = _memo(f"brief_dates:{team}", lambda: brief_store.brief_dates(team))
    i = dates.index(day) if day in dates else -1
    newer = dates[i - 1] if i > 0 else None
    older = dates[i + 1] if 0 <= i < len(dates) - 1 else None
    return render_template(
        "brief.html",
        team=TEAMS[team],
        brief=brief,
        newer=newer,
        older=older,
        others=[(t, b) for t, b in zip(others, other_briefs) if b],
        canonical=SITE_URL + brief_path(team, day),
    )


@app.route("/briefs")
@app.route("/<team>/briefs")
def briefs_archive(team=None):
    if team is not None and team not in TEAMS:
        abort(404)
    def load():
        if team:
            entries = [(team, d) for d in brief_store.brief_dates(team, limit=60)]
        else:
            entries = brief_store.recent_briefs(limit=60)
        return [b for b in brief_store.get_briefs(entries) if b]
    items = _memo(f"archive:{team}", load)
    return render_template(
        "briefs.html",
        team=TEAMS.get(team),
        items=items,
        canonical=SITE_URL + (url_for("briefs_archive", team=team) if team else "/briefs"),
    )


@app.route("/newsletter")
def newsletter_page():
    if not newsletter.enabled():
        return redirect("/", code=302)
    ref = "".join(ch for ch in request.args.get("ref", "")[:20] if ch.isalnum())
    return render_template("newsletter.html", canonical=SITE_URL + "/newsletter", source="newsletter" + (f"-{ref}" if ref else ""),
                           status=request.args.get("status"), message=_SIGNUP_MESSAGES.get(request.args.get("status")))


@app.route("/email")
def email_shortcut():
    """The short address said and shown at the end of every video."""
    return redirect(url_for("newsletter_page", ref="video"), code=302)


_SIGNUP_MESSAGES = {
    "ok": "Almost done: check your inbox and click the confirmation link.",
    "exists": "You're already on the list. Thanks!",
    "invalid": "That email address doesn't look right.",
    "limited": "Too many signups from this connection. Try again later.",
    "error": "Something went wrong on our end. Please try again in a minute.",
}


@app.route("/subscribe", methods=["POST"])
def subscribe():
    if not newsletter.enabled():
        abort(404)
    if request.form.get("website"):  # hidden field only bots fill in
        status = "ok"
    else:
        ip = (request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For") or request.remote_addr or "")
        ip = ip.split(",")[0].strip()
        try:
            status = newsletter.subscribe(request.form.get("email", ""), ip=ip,
                                          source=request.form.get("source", ""))
        except Exception as e:
            app.logger.warning("newsletter signup failed: %s", e)
            status = "error"
    if request.headers.get("Accept") == "application/json":
        return jsonify(status=status, message=_SIGNUP_MESSAGES[status]), 200 if status in ("ok", "exists") else 400
    return redirect(url_for("newsletter_page", status=status))


_PICK_MESSAGES = {
    "ok": "You're in! Check your inbox to confirm the daily email, and watch the leaderboard after the game.",
    "closed": "Picks for this game are closed. Come back for the next one.",
    "invalid": "Check your pick: a name, an email, and a score with a winner.",
    "limited": "Too many entries from this connection. Try again later.",
    "error": "Something went wrong on our end. Please try again in a minute.",
}


@app.route("/picks", methods=["GET", "POST"])
def picks_page():
    """Pick the score: guess the Eagles' next final, climb the season leaderboard. Entering joins the daily email."""
    if not newsletter.enabled():
        return redirect("/", code=302)
    from lib import picks

    game = picks.next_game()
    if request.method == "POST":
        status = "ok"
        if not request.form.get("website") and game:  # hidden field only bots fill in
            ip = (request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For") or request.remote_addr or "")
            try:
                ours, theirs = int(request.form.get("ours", "")), int(request.form.get("theirs", ""))
                status = picks.submit(game, request.form.get("email", ""), request.form.get("name", ""), ours, theirs)
                if status == "ok":
                    joined = newsletter.subscribe(request.form.get("email", ""), ip=ip.split(",")[0].strip(), source="picks")
                    status = "ok" if joined in ("ok", "exists") else joined
            except ValueError:
                status = "invalid"
            except Exception as e:
                app.logger.warning("pick failed: %s", e)
                status = "error"
        return redirect(url_for("picks_page", status=status))
    status = request.args.get("status")
    return render_template("picks.html", canonical=SITE_URL + "/picks", game=game,
                           open=bool(game) and picks.is_open(game), entries=picks.count(game["id"]) if game else 0,
                           board=picks.leaderboard(), last=picks.last_results(),
                           status=status, message=_PICK_MESSAGES.get(status))


@app.route("/about")
def about():
    return render_template("about.html", canonical=SITE_URL + "/about")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", canonical=SITE_URL + "/privacy")


def _admin_ok() -> bool:
    key = os.environ.get("ADMIN_KEY")
    if key and secrets.compare_digest(request.args.get("key", ""), key):
        session["admin"] = True
    return bool(key) and session.get("admin") is True


@app.route("/admin/comments")
def admin_comments():
    if not _admin_ok():
        abort(404)
    r = store.client()
    items = []
    for member in r.zrevrange(store.key("comments", "queue"), 0, 149):
        platform, cid = member.split(":", 1)
        if raw := r.get(store.key("comments", "item", platform, cid)):
            items.append(json.loads(raw))
    items.sort(key=lambda i: (i["status"] != "pending", -i.get("created", 0)))
    return render_template("admin_comments.html", items=items)


@app.route("/admin/comments/<platform>/<path:cid>", methods=["POST"])
def admin_comment_action(platform, cid):
    if not _admin_ok():
        abort(404)
    r = store.client()
    key = store.key("comments", "item", platform, cid)
    raw = r.get(key)
    if not raw:
        abort(404)
    item = json.loads(raw)
    action = request.form.get("action")
    if action == "approve" and request.form.get("reply", "").strip():
        item.update(status="approved", draft=request.form["reply"].strip()[:1000])
    elif action == "hide":
        item["status"] = "hide_approved"
    elif action == "dismiss":
        item["status"] = "dismissed"
    r.set(key, json.dumps(item), ex=60 * 86400)
    return redirect(url_for("admin_comments"))


@app.route("/admin/cartoons")
def admin_cartoons():
    if not _admin_ok():
        abort(404)
    from shorts import cartoons

    order = {"pending": 0, "rejected": 1, "approved": 2}
    sign = cartoons.image_url if os.environ.get("S3_BUCKET") else None
    items = [{**c, "slug": s, "url": sign(c["key"]) if sign else c.get("preview_url", "")}
             for s, c in cartoons.all_cartoons("eagles").items()]
    items.sort(key=lambda c: (order.get(c["status"], 3), c["name"]))
    counts = {k: sum(c["status"] == k for c in items) for k in order}
    return render_template("admin_cartoons.html", items=items, counts=counts)


@app.route("/admin/cartoons/<name_slug>", methods=["POST"])
def admin_cartoon_action(name_slug):
    if not _admin_ok():
        abort(404)
    from shorts import cartoons

    if request.form.get("action") in ("approved", "rejected"):
        cartoons.set_status("eagles", name_slug, request.form["action"])
    return redirect(url_for("admin_cartoons"))


@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /health\nDisallow: /admin\n\nSitemap: {SITE_URL}/sitemap.xml\n"
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
    if newsletter.enabled():
        urls.append((SITE_URL + "/newsletter", None, "monthly"))
        urls.append((SITE_URL + "/picks", None, "daily"))
    return Response(render_template("sitemap.xml", urls=urls), mimetype="application/xml")


@app.route("/health")
def health():
    return "ok", 200


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run()
