# Enabling Real Ads

The site has **ad slots** on every team page (leaderboard 728×90 above the news grid). To turn them into revenue:

## AdSense and aggregation / "repost" content

Google's policy says you **cannot** run AdSense on pages that are *only* "embedded or copied content from others without additional commentary, curation, or otherwise adding value." Pure reposts with no added value can get rejected or disabled.

Your site **does** add value: you **curate** (pick which articles to show), **organize by team**, and provide a **single dashboard** with headlines, blurbs, and source attribution. Many aggregation/curation sites are approved. To improve your chances:

- Keep **clear source attribution** (e.g. "-- NBC Sports Philadelphia", "-- PhillyVoice") on every card.
- Consider adding **short original commentary** (e.g. one line per article) or a brief intro per team.
- Ensure each page has a **distinct purpose** (e.g. "Sixers news" with your selection of links), not just a copy of one other page.

Apply and let Google review; they approve many curated news hubs. If you get a rejection, you can add more original value and reapply.

---

## Google AdSense (recommended)

1. Sign up at [google.com/adsense](https://www.google.com/adsense).
2. Get your **client ID** (format `ca-pub-XXXXXXXXXXXXXXXX`) and create an **ad unit** (e.g. display, 728×90).
3. In each template (`templates/index.html`, `index2a.html`, `index3a.html`, `index4a.html`), find the block:

   ```html
   <div class="ad-slot ad-slot-leaderboard" data-ad-type="leaderboard">
     <span class="ad-placeholder">Ad space (728×90)</span>
   </div>
   ```

4. Replace it with your AdSense code, for example:

   ```html
   <div class="ad-slot ad-slot-leaderboard">
     <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX" crossorigin="anonymous"></script>
     <ins class="adsbygoogle"
          style="display:inline-block;width:728px;height:90px"
          data-ad-client="ca-pub-XXXXXXXXXX"
          data-ad-slot="YYYYYYYYYY"></ins>
     <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
   </div>
   ```

5. Use your real **client** and **slot** values. You can add more units (e.g. sidebar 300×250) by adding more `.ad-slot` divs and pasting the matching AdSense snippet.

## Other networks

You can use the same `.ad-slot` containers for Media.net, Ezoic, or other ad scripts. Keep the container class so existing CSS (min-height, border) still applies.
