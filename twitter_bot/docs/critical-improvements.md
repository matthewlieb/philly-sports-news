# Critical improvements: making the bot feel human and less promotional

**Status: Implemented** — All items below were implemented. This doc is kept for reference.

---

Perspective: readers who dislike obviously AI content or constant website promotion. Informed by successful sports bots and 2024–2026 guidance on AI tell-tales and link strategy.

---

## 1. Promotion: every tweet ends with phillysportdaily.com

**Problem**  
Right now **every** tweet (article, satire, standalone) must end with `phillysportdaily.com`. That creates a rigid, repetitive pattern. Best practice from growth/engagement research: use the **bio link** as the main conversion surface; use **in-tweet links** for time-sensitive or high-value moments, not every post. A feed where every single tweet ends with the same domain reads as promotion-first, content-second.

**Suggestions**

- **Article/satire tweets:** Keep the domain (you’re already linking to an article; “more at phillysportdaily.com” is coherent). Optionally vary wording sometimes: “more: phillysportdaily.com” or “full story at phillysportdaily.com” so it’s not always the exact same suffix.
- **Standalone tweets (stats, hot takes, “on this day”):** Do **not** require the domain every time. Let a meaningful share (e.g. 40–50%) of standalones be pure fan content—no link, no plug. The bio already points to phillysportdaily.com; that’s enough for discovery. This reduces “every tweet is an ad” and increases trust.
- **Implementation:** Add a config or random choice for standalone: e.g. 50% of standalones omit the domain; the rest can still end with it when it fits naturally. Only call `_ensure_suffix()` for article/satire (and for the standalone subset that should include the domain).

---

## 2. One example teaches “ad copy”

**Problem**  
Example tweet: *“Check http://phillysportdaily.com for all your latest Eagles & Philly sports news.”* That’s CTA/copy, not a fan take. The model will mimic that tone and produce more “Check … for all your latest …” style lines, which feel like ads.

**Suggestion**  
Remove or replace that example. If you keep a “plug” example, make it short and casual (e.g. “Story below. phillysportdaily.com” or “More at phillysportdaily.com”) and pair it with several examples that have **no** plug at all (e.g. “Josh Harris is a bum #sixers”, “Carson Wentz: 3-0, 0 TOs …”, “Kawhi is reportedly done in San Antonio. Philly time??? #TTP”).

---

## 3. AI tell-tales we’re not guarding against

**Problem**  
Generic guidance (“sound like a fan”) isn’t enough. AI tends to overuse specific patterns that readers learn to spot: em dashes, “It’s not just about X—it’s about Y,” lists of three parallel phrases, hollow praise (“truly”, “genuinely”, “game-changing”), and safe transitions (“dive deeper”, “leverage”). Successful bots and humanization guides stress **negative instructions**: explicitly forbid these patterns.

**Suggestions**  
Add to the system/voice rules (in `run.py` and/or `voice.py`):

- **No em dashes** in tweets (or use sparingly). People rarely type — in casual tweets.
- **No** “It’s not just about X. It’s about Y.” or similar parallel structures.
- **No** list-of-three punchlines (“A, B, and C.”) as a crutch.
- **No** corporate/vague words: “leverage”, “game-changing”, “dive deeper”, “truly”, “genuinely” (unless clearly sarcastic).
- **Prefer one concrete detail** (a number, a name, a specific moment) over vague praise.

That keeps the “fan voice” but reduces the kind of polish that screams “AI.”

---

## 4. Over-prescribed openings

**Problem**  
We tell the model to “Mix in BREAKING, stats, questions, ‘This is wild.’, etc.” Those become new crutches. We already saw “So…” repeat; “This is wild.” and “BREAKING” can repeat in the same way if they’re the only options we emphasize.

**Suggestion**  
Soften to: “Vary openings. Don’t start multiple tweets in a row with the same phrase. Use whatever fits: a stat, a question, a hot take, BREAKING when it’s actually breaking, or a short reaction—no single formula.” Remove the explicit list of approved openers so the model doesn’t rotate through the same few.

---

## 5. Successful sports bots: what we’re missing

**Patterns from research**

- **Consistent personality, not template:** Bots that feel human keep one clear POV and vary **how** they say things (wording, structure, length). We have voice examples but we lock structure (article URL + phillysportdaily.com every time), which limits variety.
- **Value mix:** Engagement advice often suggests a mix: a lot of value/opinion/story, and a smaller share of direct promotion. We’re 100% “includes phillysportdaily.com” and a high share of article links; adding more link-free, plug-free standalones would align with that.
- **Natural timing/variation:** Randomizing when we add (or omit) the domain and varying the plug wording would look less mechanical than “every tweet, same suffix.”
- **Specificity:** Stats bots and “on this day” style accounts work because they’re concrete (numbers, names, dates). Our prompts already ask for stats/historical; we could stress “one specific fact or moment per tweet” more.

**Concrete additions**

- In standalone generation: explicitly allow “no link and no phillysportdaily.com” for a subset of runs.
- In article tweets: optionally allow “end with phillysportdaily.com or a short phrase like ‘more: phillysportdaily.com’” so the exact token isn’t identical every time.
- In voice: add “One concrete detail (stat, name, year) beats vague praise.”

---

## 6. Summary: high-impact changes

| Priority | Change | Why |
|----------|--------|-----|
| High | Make phillysportdaily.com **optional** on a large share of **standalone** tweets (e.g. 50%) | Reduces “every tweet is an ad”; bio link stays for discovery. |
| High | **Remove or rewrite** the “Check … for all your latest …” example | Stops teaching ad copy; keeps voice fan-first. |
| High | Add **anti-AI rules**: no em dashes, no “It’s not just about…”, no “leverage”/“game-changing”/“dive deeper”, prefer one concrete detail | Fewer obvious AI tells. |
| Medium | **Soften opening rules**: vary naturally, no fixed list of approved openers | Avoids replacing “So…” with “This is wild.” / “BREAKING” repetition. |
| Medium | **Vary plug wording** on article tweets sometimes (“more: phillysportdaily.com” vs “phillysportdaily.com”) | Same goal, less robotic pattern. |
| Low | Document “standalone = no plug” and “bio link = main conversion” in README | Aligns future edits with the strategy. |

---

## Implementation notes

- **No new dependencies.** All of the above are prompt/voice changes plus one behavioral change: for standalone, sometimes skip `_ensure_suffix()` and don’t require the domain in the standalone prompt for that run.
- **Backward compatible.** Article/satire tweets can keep current behavior; only standalone gets the “optional domain” logic and a clearer “some tweets are just fan takes” instruction.
