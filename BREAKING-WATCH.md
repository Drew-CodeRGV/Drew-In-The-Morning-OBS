# Breaking watch (continuous ingest + alerts)

A GitHub Actions job that watches public news feeds and tells the studio dashboard (and, if you turn it on, your phone) when something new, local, or hot shows up. Free on public repos. It never posts anywhere, never emails, and every item it shows is a **lead: CONFIRM BEFORE AIR**.

```
.github/workflows/breaking-watch.yml   schedule + commit + Pages rebuild request
tools/breaking_watch.py                poll feeds, dedupe, score, classify, alert
tools/trend_score.py                   dedupe + trend score (shared with the packet builder)
tools/ditm_yaml.py                     tiny YAML reader (no pip packages)
feeds.yml                              feeds, local outlets, optional score overrides
watch-keywords.yml                     place names, themes, urgent words
state/seen.json                        what has been seen / alerted (committed; compact, one story per line)
docs/breaking.json                     the file the dashboard strip fetches (committed, published by Pages)
tests/                                 python3 -m unittest discover -s tests
```

## When it runs

| Time (America/Chicago) | How often |
|---|---|
| 5:00 to 11:00 AM | every 15 minutes |
| all other hours | once an hour |

GitHub cron runs in UTC, so the workflow has two schedules: `*/15 10-17 * * *` (covers 5-11 AM in both CST and CDT) and `0 0-9,18-23 * * *` (hourly). The script converts to Central time and skips a 15-minute run that falls outside 5-11 AM unless it is the first run of the hour. GitHub may delay a scheduled run by several minutes at busy times; that is normal.

Run it by hand any time: GitHub > Actions > "Breaking watch" > Run workflow. Options: *Dry run* (fetch and score, write nothing, send nothing) and *Bootstrap* (record everything as already seen, send nothing). The very first run with no `state/seen.json` is automatically a silent bootstrap, so you never get a flood of old stories.

Scheduled workflows are switched off by GitHub after 60 days with no repository activity. The bot's own commits do not count as activity for this, so if the repo goes quiet, open Actions and click "Enable workflow", or push any commit.

## What it does each run

1. Reads `feeds.yml` and fetches every feed (RSS or Atom, 20 s timeout, in parallel; Reddit one at a time, 2 s apart). A feed that fails 6 times in a row is retried only every 6 hours. Dead or optional feeds are logged, never fatal.
2. Turns each entry into a story and clusters near-duplicates (the same event from KRGV, ValleyCentral, AP...) using `tools/trend_score.py`. One cluster = one item with a `sources` list.
3. Scores each cluster (formula in `packet/README.md`, "Dedupe + trend score") and labels it Hot / Trending / Active. Google Trends US and US-TX (daily RSS) feed the score.
4. Applies `watch-keywords.yml` and decides a level for each cluster:
   - **alert**: score is Hot, OR a place name plus an urgent word (crash, shooting, evacuation, ...) in the headline, OR an always-alert term (tornado warning, hurricane, ...) with a Valley place name or "Texas".
   - **watch**: a theme word (SpaceX, Starbase, ...), OR an Uncovered lead, OR a place name plus a Trending score.
   - Ambiguous place names (Mission, Alamo, Donna, Mercedes, Roma, Cameron, San Juan, Hidalgo, "the Valley") only count from a local outlet or together with another hit.
5. Writes `docs/breaking.json` (alert + watch items from the last 24 hours) and `state/seen.json`. Files are rewritten only on a material change (a new item, a level / label / Uncovered change) or at least once an hour, so the repo does not fill with noise commits.
6. Sends alerts (below) for items first seen in the last 3 hours that are level **alert** and not yet alerted. If a delivery fails, it is retried on the next run while the item is still fresh.
7. Commits the two files to `main` (message ends with `[skip ci]`), then asks Pages to rebuild.

### Uncovered (the scoop lead)
An item gets the purple **UNCOVERED** badge when there is Reddit / community / social buzz about a Valley story, a TX Google Trend, or heavy X engagement, **and no local outlet** (KRGV, ValleyCentral, Monitor, MyRGV, CBS 4, Daily McAllen, ...) has it. Always shown with CONFIRM BEFORE AIR. With only public feeds on a cloud runner it will fire rarely (Reddit often rate-limits GitHub's IPs); it works best when the packet's `leads` list carries X / Facebook / Reddit chatter from a research pass.

## Three alerts

**(a) Dashboard strip, always on.** The studio page (docs/index.html and each packet's page) has a "Breaking / New since build" strip at the top. It fetches `breaking.json` from the same site every 2 minutes (and when you tap Refresh), counts only items first seen **after the page was built**, and shows the count in a header badge (red if any is an alert). "Show earlier in the last 24h" lists the rest. Open from a file instead of the live site and it says the feed needs the live site.

**(b) Phone push through ntfy.sh, optional.** Only runs if the repo secret `NTFY_TOPIC` exists. Nothing about it is stored in the repo.
1. Pick a long random topic name nobody can guess, for example the output of `openssl rand -hex 12` prefixed with `ditm-`. The name is the only password on a public ntfy topic.
2. Install the **ntfy** app on your iPhone/iPad (App Store, free), tap +, "Subscribe to topic", paste the topic, leave the server as ntfy.sh.
3. Add the secret: GitHub repo > Settings > Secrets and variables > Actions > New repository secret, name `NTFY_TOPIC`, value = the topic. Or `gh secret set NTFY_TOPIC` in a terminal.
4. Check the phone path on its own (outside the repo): in a terminal run `curl -d "test" ntfy.sh/YOUR-TOPIC`; the phone should buzz. A real alert only arrives when a fresh alert-level story appears; a manual workflow run never invents one.
Optional: `NTFY_TOKEN` (secret) if you made the topic access-controlled on a self-hosted or paid server, and `NTFY_SERVER` (workflow env) if not ntfy.sh. At most 5 pushes per run, plus a "+N more" summary. Each push has the headline, source count, reasons, and the link; priority is high for Hot.

**(c) GitHub issue, optional.** Off unless the repo **variable** `BREAKING_ISSUES` is `true` (Settings > Secrets and variables > Actions > Variables). Opens an issue labeled `breaking` for the very top items only: at most 5 per run and 15 per day. Create the label once so it has a color: `gh label create breaking --color c1121f --description "Breaking watch lead: confirm before air"` (the script falls back to an unlabeled issue if the label is missing). Issues contain public headlines and links only; `@` mentions are neutralized.

## Pages deploy
`pages.yml` is manual-only; the live site is the standard "pages build and deployment" from `main` /docs. The workflow's last step calls the Pages API (`POST /repos/{repo}/pages/builds`) so the new `breaking.json` is published even if GitHub does not start a build for a bot push or because of `[skip ci]`. That step is best-effort (`continue-on-error`); if the log says it failed with 403/404, either remove ` [skip ci]` from the commit message in the workflow or set Settings > Actions > General > Workflow permissions to "Read and write". Pages typically takes 1-2 minutes to publish, so the strip is "about 15-20 minutes fresh" at worst during the 5-11 AM window.

## Settings checklist for Drew
1. Settings > Actions > General > Workflow permissions: **Read and write**.
2. Settings > Pages: source "Deploy from a branch", `main`, `/docs` (already how the site works).
3. (Optional push) Secret `NTFY_TOPIC` + ntfy app, as above.
4. (Optional issues) Variable `BREAKING_ISSUES=true` and the `breaking` label.
5. After the first commit lands, run the workflow once manually (it bootstraps silently), then watch the Actions log for "feeds ok n/m".

## Tuning
- `feeds.yml`: add or drop feeds. Mark noisy or flaky ones `optional: true`. `local_outlets` is the list that counts as local coverage; `outlet_aliases` merges sister sites (KVEO = ValleyCentral, Monitor = MyRGV).
- `watch-keywords.yml`: edit the lists; `*` at the end of a word is a stem wildcard.
- Score cut-offs: `scoring:` block in `feeds.yml` (`hot`, `trending`, and the weights; see `DEFAULTS` in `tools/trend_score.py`).
- Locally: `python3 tools/breaking_watch.py --dry-run --force --print-clusters 15`.

## Privacy and safety
Public feeds only; no logins or API keys. The ntfy topic and token live only in GitHub Secrets and are sent in the request body / header, never in a URL, a log line, or a file. Item titles from feeds are treated as text (never HTML) and only http(s) links are kept.
