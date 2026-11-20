# DITM show packet generator (Monday packet + daily briefing)

One data file per week -> one command -> every format. Nothing here ever sends email or posts.

## Regenerate (exact commands)

```bash
cd /workspace/drew-in-the-morning/packet
# 1. copy last week's file and update EVERY item (see "Weekly research" below)
cp data/packet-2026-11-23.json data/packet-YYYY-MM-DD.json     # YYYY-MM-DD = the Monday of the show
# 2. build everything (fetches fresh NWS weather, merges the 60-minute show clock from ../obs-data.json)
python3 build_packet.py data/packet-YYYY-MM-DD.json --refresh-weather --check-links
```

Flags: `--no-obs-update` (do not write cold open/jingle/up-to into obs-data.json) · `--force-latest` (let a SAMPLE build replace latest) · `--refresh-weather` (pull api.weather.gov, BRO) · `--check-links` (HEAD/GET every URL; writes `-link-check.json`; sites that bot-wall with 403 are reported as "blocked", not dead) · `--obs-data PATH` · `--out DIR` · `--no-render` (skip Chrome).
`--fetch-trends` (pull Google Trends US-TX + US for the trend score and cache them in `data/trends-cache.json`; without it a cache under 36 h old is used) · `--no-score` (skip dedupe, scoring, badges and sorting).
Requires: python3, `google-chrome`, `pdfinfo` + `pdftoppm` (poppler-utils). No pip packages.

The build FAILS (exit 2) if the PDF is not exactly 1 page or any card clips its text (it prints which). Fix by trimming print text (`short`, `pfact`, `pwhat`, `ptip`), setting `"noprint": true` on a headline, or `"print": false` on a National Desk story. Print text stays >= 7.4pt.

`data/make_sample_data.py` is how the Nov 23 sample was authored (plain Python dict -> JSON). For a new week you can either edit the JSON directly or copy that script.

## Outputs (`out/DITM-packet-<date>[-SAMPLE].*`)

| File | What |
|---|---|
| `.pdf` | One-page Letter-landscape infographic (clickable links). Attach this to the email. |
| `.png` | Page-1 preview of the PDF |
| `.txt` | Plain text, every URL, full National Desk and meme detail |
| `-email.html` | Inline-styled, table-based email body. Logo is `cid:ditm-logo`, Starship photo `cid:ditm-story-photo` |
| `-email-preview.html` | Same email with images embedded (open in a browser to check) |
| `-studio.html` | Self-contained interactive studio page: dark/light toggle, A-/A+, collapsible sections, clickable full 60-min rundown (notes, follow-ups, chyrons, links), copy-link button + new-tab link on every item. Works offline; no trackers or external assets |
| `-studio.png` | Screenshot of the studio page |
| `-sources.txt` | Every source URL by section (with link-check result if run) |
| `.json` | Normalized data (weather and show clock merged in); `-link-check.json` if checked |

Sample rule: set `meta.sample` true to show the "SAMPLE / preview" badge and `-SAMPLE` in the filenames; set it false for a real Monday packet.

## Content file format (`data/packet-YYYY-MM-DD.json`)

Top-level keys:

- `meta`: `date` (Monday, YYYY-MM-DD), `dateLabel`, `title`, `recap` (data window line), `tagline`, `handles`, `sample` (bool), `sampleLabel`.
- `headlines`: `rgv` (list, McAllen/RGV first) and `texas` (list); items `{title, short, url, source, confirm?, noprint?}`. `short` is the print text (aim <= 60 chars); the first 7 non-`noprint` RGV items and 1 Texas item print, all go in txt/email/studio. `image`: `{file, caption, credit_url, forItem}` thumbnail (must be free-licensed or ours; keep the credit).
- `nationalDesk`: 3 to 5 stories `{id, title, summary, angle, valley, detail?, links:[{label,url}], confirm?, print, pfact, pangle, pvalley, ptitle?}`. `summary` = one-line fact; `angle` = Stern/K-Rock-style conversational take; `valley` = "why it matters in the Valley". `print: true` for at most 3 (keep National Desk <= ~25% of the page); `pfact/pangle/pvalley` are the short print versions.
- `weather`: `{"mode":"nws","lat":26.2034,"lon":-98.2300,"note":...}`. The generator fills days/icons/alerts from NWS (office BRO) when run with `--refresh-weather`.
- `sports`: `highSchool` `{round, sourceNote, results:[{title,short,url,source,confirm?}], next:[...], college}`; `nfl`/`nba` `{title, scoreSource:{title,url}, scores:[[date,"AAA 1, BBB 0"]], notable:[{title,short,url}]}` (nba also `texas`); `mlb` `{title, note, notable}`. MLB is the offseason in Nov: show news, say so, no scores. Never include a score you could not verify; omit it instead.
- `memes`: `tagline`, `intro`, `memeOfTheWeek` (an item id), `levels`: Elementary / Middle School / High School, each `{level, icon, items:[{id,title,what,means,tip,links:[{label,url}],confirm:[...],pwhat,ptip}]}`.
- Every item needs a real, opened URL. An item with no URL is automatically stamped "NO VERIFIED LINK: CONFIRM BEFORE AIR". Put anything thin or single-sourced in `confirm` (string or list); it shows as a red CONFIRM tag everywhere.
- `showClock` and `rundown` are NOT in the content file. They are merged from `../obs-data.json`, which `tools/show_plan.py` generates (12 blocks A-L, 60 minutes, flex ranges; block B is "What I've Been Up To This Week"). To change the show plan, edit `tools/show_plan.py` and run `python3 tools/show_plan.py`; it rewrites `run-of-show-monday.md`, `obs-data.json`, `segues.md`, `show-principles.md`.

## Daily refresh (6 AM CT) and Monday packet: what the scheduled run does

Two modes, set by `meta.mode` (default: `monday` if the date is a Monday, else `daily`):
- `monday`: the full show packet for the 8 AM Monday show. Filename `DITM-packet-<date>`.
- `daily`: a 6 AM CT briefing that is the story bank for the NEXT Monday show (the header names the next show; the rundown is "next show"). Filename `DITM-briefing-<date>`. Studio Show Start and the clock countdown are keyed to the next show date (`meta.showDate`), not to the briefing date.

Steps (both modes):
1. Sync the repo (`Drew-CodeRGV/Drew-In-The-Morning-OBS`) so used-on-show logs and obs-data.json are current; copy yesterday's data file to `data/packet-YYYY-MM-DD.json`.
2. RGV headlines from MyRGV, Daily McAllen (`dailymcallen.com/local-news/editions/MM-DD-YYYY`), KRGV, ValleyCentral, The Monitor, Texas Tribune; Starbase/SpaceX items (county, TCEQ, FAA, Spaceflight Now). Drop anything already in the used log (see "Used on show").
3. RGV football: RGVSports (`rgvsports.com/rgv-football-playoff-schedule/`). Use the CURRENT page, scores can be edited. Note the round and next-week matchups.
4. NFL (pro-football-reference week page, NFL.com), NBA (basketball-reference), Texas teams, MLB offseason news (MLB.com, ESPN).
5. National Desk: 3 to 5 big national stories; primary or major-outlet link each; fact / take / Valley angle.
6. **Trending News** (`trending[]`, what's trending around the nation; it is shown as "Trending News" everywhere): fetch the day's top trending items (celebrity, culture, sports, viral). Each `{id, title, category, one_line, suggested_angle, source_url, source, short, teaser, verified, confirm, print, links}`. Only items with an opened URL; thin or single-sourced items get `confirm`. Block J (National + Trending) pulls these; the cold open uses `teaser`.
6b. **What's Happening in Tech** (`tech`, block J "Tech" sub-segment). Read Drew's **Fast Company Daily** from Gmail (READ-ONLY): search drew@drewlentz.com (`user-Gmail`) then drew@politiquera.com (`user-Gmail--politiquera`) for `(from:fastcompany OR subject:"Fast Company Daily") newer_than:2d`, `read_email` the newest issue, and take 3 to 5 stories: the headline, the article link from the email (open or at least confirm the URL text in the email), a one-line summary that uses only what the email says, and an on-air angle (an RGV or family angle only when it is natural, otherwise a plain tech take). Set `tech.origin = "fast-company-daily"` and `tech.issue = {from, subject, date, account}`. Skip stories that duplicate a National Desk or Trending item. If no issue arrived in the last 48 hours, run `python3 tools/tech_wires.py --text` (The Verge, TechCrunch, Ars Technica), pick 3 to 5 with the same rules, set `tech.origin = "wires"` and say so in `tech.note`; the packet then labels every item FALLBACK: TECH WIRES. Never invent a summary: if only the headline was read, say that in `confirm`.
7. Memes: check Know Your Meme, parent-guide outlets, platform-trend news; confirm popularity is real. Do not present a thin meme as big; mark CONFIRM BEFORE AIR.
8. "What I've Been Up To This Week" (`up_to[]`, `up_to_coming[]`, `up_to_script`, `up_to_meta`, block B) comes ONLY from Drew's **family calendar** (a published iCloud feed). No Gmail, no conference or work items. Run `python3 tools/family_calendar.py --mode daily --merge packet/data/packet-<date>.json` (daily briefing: past 7 days through today) or `--mode monday --today <show Monday> --merge ...` (Monday packet: previous Monday to Sunday plus a "coming up" list for the next 7 days). The feed URL is private: the tool reads it from the env var `DITM_FAMILY_ICS_URL` or the box file `/workspace/.ditm-private/family-ical-url`, and it must never be copied into the repo, a packet, a log or a message. The tool needs `pip install --user --break-system-packages icalendar recurring-ical-events` on the box (see `tools/requirements-calendar.txt`). If it exits 2 (feed unreachable), leave `up_to` empty so the packet says "Quiet week on the family calendar" and tell Drew the calendar could not be read; never fill block B from email or memory. Items are `{date, label, category, count}` in generic wording; see "Family calendar (block B)" below.
9. Date check: fetch each page and confirm its date; search results can surface old stories.
10. Build (command above). Look at the PNG preview (1 page, nothing clipped) and the studio screenshot. The build writes `coldOpen`, `jingle` and `upTo` into `../obs-data.json` (skip with `--no-obs-update`).
11. Publish: the build writes `out/latest-*` and `out/docs/` (`index.html`, `packets/<date>/...`, `packets/index.html`, `packets/latest.json`). A SAMPLE/test build does not replace `latest` unless you pass `--force-latest`. Nothing is sent or pushed by the generator.

6c. **Remembering Our Neighbors** (`obituaries`, read near the close in block L). Run `python3 tools/obituaries.py --days 7 --out /tmp/obits.json` (add `--days 15` the first time or for a two-week list) and set `obituaries` in the packet data to that JSON (it is the block the build expects). Exit code 2 means Legacy could not be read (Cloudflare challenge, 403/429 or a changed page): then OMIT the block, say so in the report, and never write names from memory. See "Remembering Our Neighbors" below.

### Cold open
Generated from the templates in `../cold-open.md` (about 45 seconds read aloud, Monday vs daily variant): weather phrase (NWS), top local items, a National Desk teaser and a Trending teaser, then the jingle. Sentences with an unfilled placeholder are dropped. Shown in the studio page as a big-text card with copy buttons.

### Used on the show (no repeats)
Every item, national story, trending item, meme and up-to event on the studio page has a "Used" toggle. Marks are saved on the device in localStorage; the "Used today" bar has Log to repo / Copy list / Clear. Log used items to the repo after the show, and skip them in the next refresh.

### Show Start and the countdown (studio page)
- "Show Start" sets the start to the current America/Chicago time rounded down to the minute; every block's time range is recomputed in the browser from the embedded offsets and durations (flex "stretch to" lines shift too). Stored in localStorage keyed by show date. "Planned start 8:00 AM" / "Started 9:03 AM" indicator and a Reset to 8:00 button. The live block is highlighted with time left. Works offline (iPad: 44pt+ targets, no horizontal scroll).
- The clock widget shows "Next: [letter] Name in m:ss" (block color), "Show starts in ..." before the show, "Show ends in ..." in the last block and "Show's over" after; amber under 60 seconds, red under 15.
- The PDF carries the clock bar and rundown with a right-aligned time column; the live features are studio-page only.

### Data format additions
- `up_to`: list of `{date, label, category, count}` from the family calendar; `up_to_coming`: same shape (Monday packet only); `up_to_script`: string; `up_to_meta`: `{calendar, window, comingWindow, status, internal, ...}`. Written by `tools/family_calendar.py --merge`. `obituaries`: the block `tools/obituaries.py` writes (`{source, sourceUrl, window, fetchedAt, items[]}`).
- `trending`: list as above.
- `meta.mode`, `meta.dataAsOf`, `meta.showEmail`, `meta.kidsTopic`.

## What's Happening in Tech (block J sub-segment)
`data["tech"]` = `{origin, issue, note, searchedAt, items[]}`; `origin` is `fast-company-daily` (from Drew's email), `wires` (fallback) or `none`. Each item: `{id, title, short, source, source_url, published, one_line, angle, verified, confirm, links[]}`. 3 to 5 items (the builder keeps at most 5). Items with no link, or `verified: false`, get CONFIRM BEFORE AIR automatically. Shown as the "What's Happening in Tech" section on the studio page (collapsed, after the National Desk, with a badge saying where it came from), in the email and txt, and as a one-line TECH row in the PDF's Trending card (one page rule still holds). In the run of show it is a ~90-second **Tech** sub-segment inside block J (still 12 blocks, J stays 8 min), with its own segue lines and chyron (`tools/show_plan.py`; the Companion mapping is unchanged: block J still sets the National Desk chyron). Local stays bigger: Drew skips Tech when local news runs long. The feeds for the fallback are `tech_feeds` in `feeds.yml` (not polled by the breaking watch).

## Dedupe + trend score

`tools/trend_score.py` runs inside the build (`score_stage`) and in the breaking watch. It never deletes a story you wrote: it merges duplicates, adds a transparent score, and flags leads.

**Dedupe.** Two stories are the same event when their URLs match after canonicalising (tracking parameters, www/m/amp, fragments and trailing slashes removed) AND their headlines overlap, or when their normalised headlines are similar: token Jaccard >= 0.60, or Jaccard >= 0.42 with 4+ shared words, or containment >= 0.75 with 5+ shared words; within 72 hours; and never when the headlines carry conflicting numbers ("2 robberies" vs "3 robberies") or conflicting places. A digest page linked by several different stories (a daily briefing) does not merge them. Precision beats recall: a missed duplicate costs one extra line; a wrong merge hides an event. The kept item gets `sources[]`; a merged duplicate's link is added to the kept item's links. National Desk stories are never dropped; every extra outlet linked under a National or Trending story counts as coverage of it. List priority for a duplicate: National Desk > RGV > Texas > Trending > leads.

**Score (0-100, shown in the badge tooltip as "Score 38: 5 outlets 30 + recency 8 ...").**

| part | formula | max |
|---|---|---|
| outlets | 6 x distinct outlets (sister sites count once) | 30 |
| recency | 20 x 0.5^(age_hours / 12), newest coverage; no timestamp = 8 | 20 |
| X | 20 x min(1, log10(1 + engagement + 25 x posts) / 4) | 20 |
| Google Trends | 20 if the story matches a US-TX trending term, 12 if US | 20 |
| Reddit / Facebook chatter | 10 x min(1, log10(1 + engagement + 5 x posts) / 2.5) | 10 |

Labels: **Hot** >= 45, **Trending** >= 27, otherwise **Active**. (Overrides: `scoring:` in `feeds.yml`.) A Google Trends match is by the trend's news-item URL, a similar headline, or the trend's words all appearing in the story.

**Uncovered** = community/social buzz (chatter, X, or a TX Google Trend) about a story with Valley relevance that no local outlet covers and that has no loose match against any local story. Shown as UNCOVERED with CONFIRM BEFORE AIR: it is a scoop lead, never a fact.

**Where it shows.** Studio page: HOT / TREND / ACTIVE badge with score on each item, an UNCOVERED badge, "+N sources", and a Sort button (by score or editorial order); each section header shows counts and Hot/Trend tallies. PDF: only `HOT`, a red `▲` for Trending, and `UNCOV` (Active stays unmarked; the page stays one page). Email: colored `HOT 52` / `TREND 31` chips. Text file: `[HOT 52]` / `[TREND 31]` / `[ACT 14]` prefixes, `[UNCOVERED LEAD: CONFIRM BEFORE AIR]`, and a STORY SCORES summary line. The PDF, email and text keep your editorial order (Hot items first); only the studio page sorts by score.

**Optional per-item data** you can add to any story in the data file (the daily research pass fills these when it has them): `published` (ISO time), `x` `{posts, engagement}`, `chatter` `{posts, engagement}` (or a list of those), `valley` (true if it is a Valley story). A top-level `leads` list (same shape as a headline: `title`, `url`, `source`, optional `x`/`chatter`) holds social/community-only items; they are scored and can come out Uncovered. `meta.score: false` turns scoring off for one file.

## Studio page: collapsed by default
Every section and every rundown block (A-L) loads collapsed to its header row (letter, color, title, time column for blocks, item count, badges). Tap a header to open it (44pt+ targets). **Expand all / Collapse all** work on every section and block. The open/closed state is kept per browser tab in `sessionStorage` (reload keeps it; a new tab starts collapsed again); a link like `#headlines` opens its section. The clock, countdown, Show Start button, Used-today bar and the Breaking strip stay visible. The PDF, email and txt are unchanged by this.

## Breaking strip
The studio page fetches `breaking.json` (same site) every 120 s; see `../BREAKING-WATCH.md`. The strip counts only items first seen after the page was built.

## Emailing the packet (draft only until Drew approves)

Use the `user-Gmail` connector (drew@drewlentz.com) tools `create_draft` / `send_email` (or `user-Gmail--politiquera`, drew@politiquera.com) with `attachments` as base64 `[{filename, mimeType, content, inline?}]`, up to 25 MB total: the PDF (`application/pdf`), plus `assets/DITM_SunLogo.png` and `assets/starship_thumb.jpg` as inline images with `content-id` `ditm-logo` / `ditm-story-photo` when the connector supports it, and `body` = the contents of `-email.html`. If inline cid is not supported, send the `-email-preview.html` body (images as data URIs; some clients strip them) with the PDF attached. NEVER send without an explicit approval naming the recipient. The generator does not send anything.

## Assets and credits

`assets/DITM_SunLogo.png` (copy of `../logo/`); `assets/starship_thumb.jpg` is a file photo of Starship by Steve Jurvetson, CC BY 2.0 (Wikimedia Commons), credited on the page. `raw/` holds fetched source pages from the sample's research.


## Family calendar (block B)
`tools/family_calendar.py` turns Drew's family calendar into the block B script and list. Settings that are safe to keep in the repo live in `family-calendar.yml`:
- `NAME_KIDS_ON_AIR: false` (default). Flip to `true` (or set env `DITM_NAME_KIDS_ON_AIR=true`) to name the kids from the `kids:` list; each kid can also get a `role` ("our son", "our daughter") used when names are off. Adults outside the family are never named either way.
- `household` (spoken as "the Lentz house"), `known_places` (school/place names allowed inside festival and holiday titles), `extra_exclude` (extra words to always leave off the air).
- Labels are built from rules, not copied from titles. Included: school events, concerts and recitals, games/meets/practices, festivals and parades, holiday events, clubs and classes (chess, dance, cotillion, scouts), community events, trips. Always left off: medical or health, grooming, bills and money, work admin, support appointments, pick-ups and drop-offs, routine workouts, private reservations and dinners, other people's parties, birthdays and retirements. **When unsure it is left off.** Only a count of left-off items is kept (`up_to_meta.internal`, shown on the studio page and txt as an internal note, never read on air).
- Recurring events are expanded (RRULE, America/Chicago) and collapsed to one line each ("chess club twice"). Cancelled events are skipped.
- Output fields: `up_to` (the week that was), `up_to_coming` (Monday packet only: the next 7 days), `up_to_script` (20 to 40 seconds, light, ends with one question for Jess; "Quiet week on the family calendar" plus a riff prompt when nothing qualifies), `up_to_meta` (calendar, windows, banner, internal note).
- `tools/show_plan.py` block B talking points describe the same rules; `obs-data.json` `upTo` carries the script and the items.

## Remembering Our Neighbors (obituaries)
`tools/obituaries.py` reads The Monitor's obituaries from Legacy.com (the McAllen page, `https://www.legacy.com/us/obituaries/local/texas/mcallen?publisher=The+Monitor`), newest first, `&page=N` until a page is older than the window. It reads the JSON Legacy embeds in the public page (no API, no login). Legacy's Cloudflare answers Python's urllib with a bot challenge, so the tool shells out to `curl` with a normal browser User-Agent; if Legacy ever challenges that too (HTTP 403) the tool exits 2 and a real browser is needed. If it answers 429, wait a few minutes (it rate-limits repeated pulls) and run it once more.
- Per person it keeps only `{id, name, age, city, died, published, firstPublished, funeralHome, url}`: age, city and funeral home only if the notice lists them, `published` is the most recent day The Monitor ran the notice, `url` is the Legacy link. The obituary text is never stored, so there is no cause of death anywhere, and nothing is inferred (babies and unclear ages stay blank). Duplicate person records for one notice are merged (same death date, name inside a fuller name).
- Window: `--days 7` (the routine) or `--days 15` (a two-week list). `days` counts today.
- Studio page: section "Remembering Our Neighbors" (collapsed like every section, nav link "Neighbors", chip L) with the on-air read, a Copy read button, and names grouped by week, newest first, each name linked to its Legacy obituary. Email and txt carry the full list. The PDF carries one short footer note ("Obituaries: N on studio page") only; the one-page build check still has to pass.
- On air (block L, after the memes and before the look-ahead and sign-off, about 45 seconds): the read is auto-built from the newest seven days, names with age and town, six at most; Drew skips any name he is unsure of. Never say how anyone died.
- Block structure A to L and the Companion mapping (`chyrons[0]`, `headlines[0]`) are unchanged: the L additions are appended.


## Studio page layout (v6)
- Every section is a full-width horizontal bar when collapsed, one per row, all the same height (fixed bar height; at 700 px and up the title, the full subtitle, the count and badges and the arrow all sit on the one bar, with nothing truncated; on phones long subtitles clip with an ellipsis). Tapping a bar expands it in place, full width, and flows its cards in 2 to 4 columns (about 320 px minimum per card).
- The page always scrolls natively. Cause of the old phone "no scroll": the whole header (logo, title, Show Start, six tool buttons, the clock) plus the Used bar were both `position: sticky`, together about 640 px of an 844 px phone screen (680 of 740 on a small one), so almost nothing was left to scroll and the content slid under them. Below 1000 px the header and Used bar now scroll away and only a 44 px mini clock bar stays pinned; at 1000 px and up the header is sticky but compact (tools and recap moved to a normal row under it).
- The A-L show clock bar and the section pills swipe sideways on phones (44 px minimum tap targets).
