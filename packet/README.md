# DITM Monday show packet generator

One data file per week -> one command -> every format. Nothing here ever sends email or posts.

## Regenerate (exact commands)

```bash
cd packet
# 1. copy last week's file and update EVERY item (see "Weekly research" below)
cp data/packet-2026-11-23.json data/packet-YYYY-MM-DD.json     # YYYY-MM-DD = the Monday of the show
# 2. build everything (fetches fresh NWS weather, merges the 60-minute show clock from ../obs-data.json)
python3 build_packet.py data/packet-YYYY-MM-DD.json --refresh-weather --check-links
```

Flags: `--refresh-weather` (pull api.weather.gov, BRO) · `--check-links` (HEAD/GET every URL; writes `-link-check.json`; sites that bot-wall with 403 are reported as "blocked", not dead) · `--obs-data PATH` · `--out DIR` · `--no-render` (skip Chrome).
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
- `showClock` and `rundown` are NOT in the content file. They are merged from `../obs-data.json`, which `tools/show_plan.py` generates (13 blocks A-M, 60 minutes, flex ranges). To change the show plan, edit `tools/show_plan.py` and run `python3 tools/show_plan.py`; it rewrites `run-of-show-monday.md`, `obs-data.json`, `segues.md`, `show-principles.md`.

## Weekly research (what the Monday scheduled run does)

1. Weekend/Monday morning: RGV headlines from MyRGV, Daily McAllen (`dailymcallen.com/local-news/editions/MM-DD-YYYY`), KRGV, ValleyCentral, The Monitor, Texas Tribune; Starbase/SpaceX items (county, TCEQ, FAA, Spaceflight Now).
2. RGV football: RGVSports (`rgvsports.com/rgv-football-playoff-schedule/`). Use the CURRENT page, scores can be edited (the Rowe opponent changed once). Note the round and the next-week matchups.
3. NFL (pro-football-reference week page, NFL.com), NBA (basketball-reference), Texas teams, MLB offseason news (MLB.com, ESPN).
4. National Desk: pick 3 to 5 big national stories; get a primary or major-outlet link each; write fact / take / Valley angle.
5. Memes: check Know Your Meme, parent-guide outlets, news about platform trends; confirm popularity is real (the sample used X post counts as a sanity check, and flagged TikTok-side trends). Do not present a thin meme as big; mark CONFIRM BEFORE AIR.
6. Date check: fetch each page and confirm its date; search results can surface old stories (a July AA outage story was rejected this way).
7. Build (command above), look at the PNG preview (1 page, nothing clipped) and the studio screenshot.

## Emailing the packet (draft only until Drew approves)

Use the `user-Gmail` connector (drew@drewlentz.com) tools `create_draft` / `send_email` (or `user-Gmail--politiquera`, drew@politiquera.com) with `attachments` as base64 `[{filename, mimeType, content, inline?}]`, up to 25 MB total: the PDF (`application/pdf`), plus `assets/DITM_SunLogo.png` and `assets/starship_thumb.jpg` as inline images with `content-id` `ditm-logo` / `ditm-story-photo` when the connector supports it, and `body` = the contents of `-email.html`. If inline cid is not supported, send the `-email-preview.html` body (images as data URIs; some clients strip them) with the PDF attached. NEVER send without an explicit approval naming the recipient. The generator does not send anything.

## Assets and credits

`assets/DITM_SunLogo.png` (copy of `../logo/`); `assets/starship_thumb.jpg` is a file photo of Starship by Steve Jurvetson, CC BY 2.0 (Wikimedia Commons), credited on the page. `raw/` holds fetched source pages from the sample's research.
