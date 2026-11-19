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
6. Trending (`trending[]`): fetch the day's top trending items (celebrity, culture, sports, viral). Each `{id, title, category, one_line, suggested_angle, source_url, source, short, teaser, verified, confirm, print, links}`. Only items with an opened URL; thin or single-sourced items get `confirm`. Block J (National + Trending) pulls these; the cold open uses `teaser`.
7. Memes: check Know Your Meme, parent-guide outlets, platform-trend news; confirm popularity is real. Do not present a thin meme as big; mark CONFIRM BEFORE AIR.
8. "What I've Been Up To This Week" (`up_to[]` and `up_to_script`, block B), past 7 days. Sources, in order: (a) Drew's calendar, if a calendar tool is connected (none was available on the build box on Nov 18, 2026, so the packet says "calendar not connected" in `up_to_meta.calendar`); (b) fallback: non-spam Gmail, READ-ONLY (sent-mail logs of talk proposals, public event confirmations). Each event `{date, short, title, type: conference|presentation|meeting|appearance, who: Drew|Jess, link (public URL or null), source}`. Privacy rules: include only public-facing items; exclude personal, medical, financial, legal, school/family and client-confidential items and private 1:1 meetings; never name private individuals; never invent events; mark every item CONFIRM BEFORE AIR (the generator stamps it). Say "submitted" for proposals, never "accepted" or "speaking at" unless confirmed. `up_to_script` is a conversational paragraph. If there are no events: `up_to` is `[]`, the script reads "Quiet week on the calendar..." and the packet shows "No calendar events found".
9. Date check: fetch each page and confirm its date; search results can surface old stories.
10. Build (command above). Look at the PNG preview (1 page, nothing clipped) and the studio screenshot. The build writes `coldOpen`, `jingle` and `upTo` into `../obs-data.json` (skip with `--no-obs-update`).
11. Publish: the build writes `out/latest-*` and `out/docs/` (`index.html`, `packets/<date>/...`, `packets/index.html`, `packets/latest.json`). A SAMPLE/test build does not replace `latest` unless you pass `--force-latest`. Nothing is sent or pushed by the generator.

### Cold open
Generated from the templates in `../cold-open.md` (about 45 seconds read aloud, Monday vs daily variant): weather phrase (NWS), top local items, a National Desk teaser and a Trending teaser, then the jingle. Sentences with an unfilled placeholder are dropped. Shown in the studio page as a big-text card with copy buttons.

### Used on the show (no repeats)
Every item, national story, trending item, meme and up-to event on the studio page has a "Used" toggle. Marks are saved on the device in localStorage; the "Used today" bar has Log to repo / Copy list / Clear. Log used items to the repo after the show, and skip them in the next refresh.

### Show Start and the countdown (studio page)
- "Show Start" sets the start to the current America/Chicago time rounded down to the minute; every block's time range is recomputed in the browser from the embedded offsets and durations (flex "stretch to" lines shift too). Stored in localStorage keyed by show date. "Planned start 8:00 AM" / "Started 9:03 AM" indicator and a Reset to 8:00 button. The live block is highlighted with time left. Works offline (iPad: 44pt+ targets, no horizontal scroll).
- The clock widget shows "Next: [letter] Name in m:ss" (block color), "Show starts in ..." before the show, "Show ends in ..." in the last block and "Show's over" after; amber under 60 seconds, red under 15.
- The PDF carries the clock bar and rundown with a right-aligned time column; the live features are studio-page only.

### Data format additions
- `up_to`: list as above; `up_to_script`: string; `up_to_meta`: `{window, calendar, note, jess}`.
- `trending`: list as above.
- `meta.mode`, `meta.dataAsOf`, `meta.showEmail`, `meta.kidsTopic`.

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
