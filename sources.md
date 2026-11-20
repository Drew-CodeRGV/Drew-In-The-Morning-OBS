# Drew in the Morning: community monitoring sources (read only)

## Facebook (box browser is signed in to Drew's Facebook; never post, comment, react, join or message)
- RGV Cheezmo (Facebook group): URL still TBD. Nov 19 Facebook search found no page/group by that exact name; closest match is Nomorecheezmeh (below). Search URL used: https://www.facebook.com/search/top?q=RGV%20Cheezmo
- Nomorecheezmeh (Frank Mar blog, news + satire, 112K followers; verify before air): https://www.facebook.com/nomorecheezmeh
- RGV.me (community stories, 179K followers): https://www.facebook.com/RGV.ME

- The Monitor (McAllen newspaper) Facebook page: https://www.facebook.com/monitornews
- KRGV Channel 5 News (Weslaco) Facebook page: https://www.facebook.com/channel5news

## Reddit (readable logged out on www.reddit.com; old.reddit forces login)
- r/RioGrandeValley: https://www.reddit.com/r/RioGrandeValley/new/
- r/RGVCircleJerk: https://www.reddit.com/r/RGVCircleJerk/new/ (satire, so verify elsewhere)
- r/Texas: https://www.reddit.com/r/texas/new/ (Texas-wide politics and news; also check /top/?t=day)
- r/RGV, r/McAllen, r/Brownsville, r/RGVEvents (when reachable)

Community posts are leads: confirm elsewhere, or mark them "community chatter, CONFIRM BEFORE AIR".
- Drew's account follows Nomorecheezmeh and RGV.me (as of 2026-11-18)
- Things To Do In The RGV (private group, 50.6K members, Drew is a member; events and local happenings): https://www.facebook.com/groups/5774642885929554/

- Nov 19, 2026: Reddit was not reachable from the box (block page on www.reddit.com JSON and HTML); use a browser session next run.

## Chisme (local social buzz; tools/chisme.py; read only, never log in, post, comment, react, join or message)
- Reddit public JSON/RSS: r/RGV, r/McAllen, r/Brownsville, r/Harlingen, r/Edinburg, r/riograndevalley (and r/RioGrandeValley): `https://www.reddit.com/r/<sub>/top.json?t=week`, `hot.json`, `hot/.rss`. Nov 19, 2026 from the box: JSON 403, RSS 429 (use the box browser and the capture file).
- Facebook: the watch-list pages above (The Monitor, KRGV, Nomorecheezmeh, RGV.me, Things To Do In The RGV). Logged-out fetch returns only the page shell; read them in the signed-in box browser and write them to `packet/data/chisme-capture-<date>.json`.
- Instagram: public endpoints (`/explore/tags/<tag>`, `/api/v1/tags/web_info`) are login-walled or 404, so skipped and reported, never faked.
- Safety rules and the RUMOR badge are in `packet/README.md` ("Chisme").

## Obituaries (Legacy.com, public page, read by tools/obituaries.py)
- **The Monitor obituaries, McAllen, TX on Legacy.com**: https://www.legacy.com/us/obituaries/local/texas/mcallen?publisher=The+Monitor (add `&page=2`, `&page=3` for older pages). Feeds the Lifestyle section's "Remembering Our Neighbors" list (name, age and town only). Each name links to its own Legacy notice, e.g. `https://www.legacy.com/us/obituaries/themonitor/name/<name>-obituary?id=<id>`.
- Only name, age, city, death date, run date, funeral home and link are kept; no cause of death, ever.
- Reachability (Nov 19, 2026): HTTP 200 with a browser User-Agent via curl; Python urllib gets a Cloudflare bot challenge (403); repeated pulls can hit HTTP 429 (wait and retry). Pages overlap a little and a Monitor-wide browse page (`https://www.legacy.com/us/obituaries/themonitor/browse`) also exists but lists people outside the McAllen filter, so it is not used.

## Family calendar (block B, private feed)
- Drew's FAMILY calendar, a published iCloud feed read by `tools/family_calendar.py`. The URL is private and lives only on the box (`/workspace/.ditm-private/family-ical-url`) or in the env var `DITM_FAMILY_ICS_URL`; it is never stored in this repo. Block B uses nothing else (no Gmail).

## Email newsletters (Drew's Gmail, READ-ONLY through the Gmail connector)
- **Fast Company Daily** (what's-happening-in-tech section, block J "Tech" sub-segment). Looked up each morning in drew@drewlentz.com first, then drew@politiquera.com (and Outlook if connected): search `(from:fastcompany OR subject:"Fast Company Daily") newer_than:2d`, read the newest issue, take 3 to 5 stories with the link from the email.
- Status on Nov 19, 2026, 6:25 AM CT: **no Fast Company Daily issue found** in either Gmail account or Outlook (searched `fastcompany`, "Fast Company", the subject, spam/trash included). The only Fast Company mail is Premium subscription receipts from subscriptions@fastcompany.com / care@fastcompany.com (newest Oct 24, 2023). Drew needs to confirm he is subscribed at https://www.fastcompany.com/newsletters (that page bot-blocks the box, so open it in a browser) and which address it goes to. Until an issue arrives the section uses the tech wires and says FALLBACK.
- Fallback tech wires (no login, RSS verified 2026-11-19): The Verge https://www.theverge.com/rss/index.xml · TechCrunch https://techcrunch.com/feed/ · Ars Technica https://feeds.arstechnica.com/arstechnica/index (listed under `tech_feeds` in feeds.yml; `python3 tools/tech_wires.py --text` lists the last 48 hours). Fast Company's own website feed https://www.fastcompany.com/latest/rss exists but is disabled: it is not the Daily.
