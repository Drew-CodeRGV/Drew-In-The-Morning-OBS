# Drew in the Morning — OBS collateral

On-screen text and logos for the Monday 8:00 AM CT livestream. **`obs-data.json` is the only source of show copy.** A build script turns it into one text file per line. A switcher copies the active block into `current/` so OBS can refresh.

The show is an **open menu of story blocks**, not a rigid clock. Suggested start times add up to about an hour. During the show, jump to any block by letter or order number.

New to OBS? Follow **[OBS-setup.md](OBS-setup.md)** from the top.

The live studio page is **[docs/index.html](docs/index.html)**, a copy of the latest packet studio file. Older packets are listed at [docs/packets/index.html](docs/packets/index.html). GitHub Pages, if this private repo is allowed to serve `main` `/docs`, is `https://drew-codergv.github.io/Drew-In-The-Morning-OBS/`. The owner login is Drew-CodeRGV, so `https://drew-coderGV.github.io/...` is not this repository. Enabling Pages from this environment returned HTTP 403 `Resource not accessible by integration`. The repo stays private. `.github/workflows/pages.yml` is a manual deploy for when Pages is permitted.

## Layout

| Path | Role |
|---|---|
| `obs-data.json` | Edit this, or regenerate it with `python tools/show_plan.py`. Schema v3. |
| `scripts/build.py` | Regenerates the text files. Run it after every edit. |
| `scripts/live.py` | `next`, `prev`, `goto`, `skip`, chyron and headline changes. |
| `companion/` | Stream Deck via Bitfocus Companion. See [companion/README.md](companion/README.md). |
| `current/` | What is on screen right now. Point OBS here. |
| `chyrons/`, `headlines/`, `segment-titles/` | One `.txt` per on-screen item, for the whole episode. |
| `ticker/ticker.txt` | The scrolling ticker, one line. |
| `scenes/` | Show title, date, BRB card, account list, call-in promo lines. |
| `images/logo/` | Official logos. See OBS-setup for which file goes on which scene. |
| `overlay/` | Browser-source lower third, headline card, pre-show, outro, and BRB. |
| `run-of-show-monday.md` | Spoken 60-minute menu with time ranges. **CONFIRM BEFORE AIR** flags stay in this file. |
| `show-principles.md` | Format, tone, and flex rules. |
| `segues.md` | Spoken bridges. Also stored on `obs-data.json`. |
| `sources.md` | Community pages to monitor. Read only. |
| `call-ins.md` | How listeners reach the show. Draft until a route is confirmed. |
| `social-calendar.md` | Weekly post calendar. **Draft. Nothing here is posted.** |
| `research.md` | Background. Not a script. |
| `tools/show_plan.py` | Rewrites the run of show, segues, principles, and `obs-data.json`. |
| `packet/` | Monday packet generator and the Nov 23 sample outputs. |
| `show-notes/segment-index.md` | Generated cue sheet, including every CONFIRM BEFORE AIR line. Do not edit. |
| `playlist.json` | Generated map the switcher reads. Do not edit. |

Chyron files are two lines: the name (primary), then the subtitle (secondary). `current/chyron.txt` keeps both. `current/chyron-primary.txt` and `current/chyron-secondary.txt` split them so OBS can style each line.

Block letters come from the segment id (`A-…`, `B-…`). The scripts do not contain this week's titles. When the lineup changes, replace the JSON (and the run of show, if the spoken script changed) and rebuild.

## Commands

Python 3.9 or newer. Standard library only. No install step.

```bash
python scripts/build.py
python scripts/live.py list
python scripts/live.py reset
python scripts/live.py repl
```

In the repl, during the show:

```text
next                 next block, including ones marked skippable
prev
goto A               jump to a block letter
goto <order|id>      order number or id from obs-data.json
skip                 jump forward to the next block that is not skippable
chyron next          next lower-third on this block
headline next        next headline on this block
chyron call          cycle the call-in promo plates
chyron host          show-level host plate (also jess, socials, comment)
status
quit
```

`skip` will not jump over a block whose `skippable` flag is false. That includes the signature block. `goto` can still open any block, in any order. Suggested times are labels, not cues you have to hit.

`chyron call` rotates the plates in `callIns.chyrons`. The longer read-out lines are `scenes/call-promo-01.txt` and the following files, or all of them in `scenes/call-promos.txt`.

`python scripts/live.py serve` is only needed for the browser overlays. Text sources and image sources do not need it.

`build.py` stops if any chyron line is longer than `chyronMaxChars` (60 in the current file). It does not trim a line to make it fit.

## Weekly refresh

News has to be re-verified **Sunday night before the Monday show**. The last check is `show.disclaimer` in `obs-data.json` (copied to `show-notes/disclaimer.txt`). Read the **CONFIRM BEFORE AIR** lines in `run-of-show-monday.md` and in the generated `show-notes/segment-index.md` before anything goes on screen.

1. Re-check `run-of-show-monday.md`, `show-notes/segment-index.md`, and `call-ins.md`. Change `obs-data.json` (or `tools/show_plan.py`, then run it). Do not add a line you have not re-verified, and do not hand-edit the generated `.txt` files.
2. If the spoken script changed, edit `run-of-show-monday.md`. Segues live in `segues.md` and in `obs-data.json`.
3. `python scripts/build.py`
4. `python scripts/live.py list`, then `python scripts/live.py reset` so the open is the first block.

`social-calendar.md` is a draft calendar. Do not post from it until it is approved. `research.md` stays as context. It is not loaded on screen.

Schema v3 blocks are **flex** (trim or stretch), not a skippable/core split. `goto A` still jumps by letter. `skip` only jumps a block when `obs-data.json` still marks it `skippable`.
