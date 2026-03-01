# X API 503 (Service Unavailable) — causes and troubleshooting

A **503** from the X API means their server couldn’t handle the request (temporary). It’s not an issue with your app or credentials.

## Common causes

- **Server overload or maintenance** — X’s servers are busy or under maintenance.
- **Rate / capacity** — Sometimes 503 is returned instead of 429 when you hit internal capacity limits (even with quota left).
- **Specific endpoints** — More often reported on e.g. `POST /2/tweets`, `GET /2/users/me`, DM endpoints; can be inconsistent (some requests succeed, others 503).
- **Backend issues** — Failures between X’s internal services (e.g. cache ↔ backend).
- **Regional issues** — Problems in a specific region; moving app region can help if you have that option.
- **Request content** — Certain parameters can trigger 503 (e.g. quoting a user who blocked you, unsupported or oversized media).

## What we do in this project

- **Retry with backoff** — Up to 3 attempts with 10s, 20s (or `Retry-After` if X sends it, capped at 120s).
- **Soft failure** — If the only error is 503 or 429, the job exits successfully so the next scheduled run tries again.
- **No rapid repeated calls** — One tweet per run; scheduler runs at most a few times per day.

## If 503 keeps happening

1. **Wait and retry** — Usually temporary; wait a few minutes and run again.
2. **Check status** — [X API status](https://api.twitter.com/) or status.x.com for incidents/maintenance.
3. **Logs** — Check app logs for the full error and any other clues.
4. **Retry-After** — If X sends a `Retry-After` header, we use it (capped at 120s) before retrying.
5. **Request shape** — If it’s always the same kind of request (e.g. with media), try without media or with smaller/supported format.
6. **Community** — Search or post on [X Developers community](https://devcommunity.x.com/) for similar reports.
7. **X support** — If it persists, contact X with request/response and timestamps.

## References

- X API rate limits and status pages (developer.x.com).
- Community reports: 503 on POST /2/tweets and GET /2/users/me; often intermittent.
