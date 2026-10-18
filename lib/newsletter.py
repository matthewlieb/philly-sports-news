"""The daily email, sent through Buttondown (https://buttondown.com).

Buttondown keeps the subscriber list, the confirmation emails, the unsubscribe links and the mailing-address footer
the law requires; this module only adds subscribers from the site's signup form and sends each morning's briefs.
Everything is off until BUTTONDOWN_API_KEY is set.
"""
import os
import re

import requests

from lib import briefs, store
from lib.teams import SITE_NAME, SITE_URL, TEAMS, TEAM_SLUGS, brief_url

_API = "https://api.buttondown.com/v1"
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}$", re.I)
SIGNUPS_PER_IP_PER_HOUR = 5


def enabled() -> bool:
    return bool(os.environ.get("BUTTONDOWN_API_KEY"))


def _headers(**extra) -> dict:
    return {"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}", "X-API-Version": "2026-04-01", **extra}


def subscribe(email: str, ip: str = "", source: str = "") -> str:
    """Add a subscriber, who then gets Buttondown's confirmation email. Returns "ok", "exists", "invalid" or "limited"."""
    email = email.strip().lower()
    if len(email) > 254 or not _EMAIL.match(email):
        return "invalid"
    r = store.client()
    k = store.key("signups", "ip", ip or "unknown")
    count = r.incr(k)
    if count == 1:
        r.expire(k, 3600)
    if count > SIGNUPS_PER_IP_PER_HOUR:
        return "limited"
    body = {"email_address": email, "type": "unactivated", "metadata": {"source": source[:100]}}
    if ip:
        body["ip_address"] = ip
    resp = requests.post(f"{_API}/subscribers", headers=_headers(), json=body, timeout=15)
    if resp.status_code == 400 and "already" in resp.text.lower():
        return "exists"
    if resp.status_code == 400 and "email" in resp.text.lower():
        return "invalid"
    resp.raise_for_status()
    r.incr(store.key("signups", briefs.local_today()))
    return "ok"


def _brief_markdown(brief: dict) -> str:
    parts = [f"**{brief['summary']}**"]
    for sec in brief["sections"]:
        if sec["heading"]:
            parts.append(f"## {sec['heading']}")
        parts += sec["paragraphs"]
        names = list(dict.fromkeys(s["source"] for s in sec["sources"]))
        if names:
            urls = {s["source"]: s["url"] for s in sec["sources"]}
            parts.append("*Sources: " + ", ".join(f"[{n}]({urls[n]})" for n in names) + "*")
    return "\n\n".join(parts)


def daily_email(day: str, lead: str = "eagles") -> tuple[str, str] | None:
    """(subject, markdown body): the lead team's full brief, then one line on each other team's."""
    found = dict(zip(TEAM_SLUGS, briefs.get_briefs([(t, day) for t in TEAM_SLUGS])))
    if not found.get(lead):
        lead = next((t for t in TEAM_SLUGS if found[t]), None)
    if not lead:
        return None
    main = found[lead]
    body = [f"# {main['headline']}", _brief_markdown(main),
            f"[Read it on the site, with every source]({brief_url(lead, day)}?utm_source=email)"]
    others = [(t, found[t]) for t in TEAM_SLUGS if t != lead and found[t]]
    if others:
        body.append("## Around Philly today")
        body += [f"- **{TEAMS[t]['name']}:** [{b['headline']}]({brief_url(t, day)}?utm_source=email)" for t, b in others]
    body.append(f"---\n\n*{SITE_NAME} writes these briefs each morning with the help of AI, working only from the "
                "reporting it links to. Spot an error? Just reply to this email.*\n\n"
                f"*Know a fan who'd want this? Send them to {SITE_URL}/newsletter*")
    return f"{TEAMS[lead]['name']}: {main['headline']}", "\n\n".join(body)


def send_daily(day: str | None = None) -> bool:
    """Send today's email once. True if it was sent by this call."""
    if not enabled():
        print("Daily email: BUTTONDOWN_API_KEY not set, skipping.")
        return False
    day = day or briefs.local_today()
    r = store.client()
    sent_key = store.key("email", "sent", day)
    if r.get(sent_key):
        print(f"Daily email for {day} already sent.")
        return False
    email = daily_email(day)
    if not email:
        print(f"Daily email: no briefs for {day}.")
        return False
    subject, body = email
    resp = requests.post(f"{_API}/emails", timeout=30, headers=_headers(**{"X-Buttondown-Live-Dangerously": "true"}),
                         json={"subject": subject[:200], "body": body, "status": "about_to_send"})
    if not resp.ok:
        raise RuntimeError(f"Buttondown send failed ({resp.status_code}): {resp.text[:500]}")
    r.set(sent_key, resp.json().get("id", "sent"), ex=7 * 86400)
    print(f"Daily email sent: {subject}")
    return True
