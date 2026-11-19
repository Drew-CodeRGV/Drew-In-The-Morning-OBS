# OBS setup for Drew in the Morning

A sequential setup for someone who has opened OBS, added a camera, and not done much else. You do not need a scene for every segment. Two live scenes share the same text sources. A small Python script swaps the words in `current/`, and OBS re-reads the files.

The words on screen come from `obs-data.json`. This guide does not name blocks, because the lineup changes. Use `python scripts/live.py list` to see this week's letters, order numbers, and which blocks are skippable or signature.

The rundown is a menu. Suggested start times are not a clock. You jump to a block when the conversation gets there.

Do this on the computer that runs OBS. Python 3.9+ is required (`python3 --version`). There is no package to install.

## 1. Generate the text files

In a terminal, go to this folder and run:

```bash
python scripts/build.py
python scripts/live.py list
```

`list` prints each segment's order number, start time, and title, and marks skippable segments and Jess segments. That list is the rundown the switcher will follow.

If build stops with `ERROR` and a character count, a chyron line is over `chyronMaxChars`. Shorten that primary or secondary in `obs-data.json` and run build again. Do not shorten it in a `.txt` file. The next build would overwrite the file.

## 2. Decide how text gets on screen

Use one of these. You can mix them.

**Text sources (simplest).** OBS → Sources → + → **Text (FreeType 2)**. On Windows the item may be named **Text (GDI+)**. Check **Read from file**, then browse to a file in this folder. Prefer FreeType 2 if a middle dot (`·`) shows up as the wrong character.

**Browser sources (one lower third instead of several text boxes).** In a second terminal, leave this running for the whole show:

```bash
python scripts/live.py serve
```

In OBS, Sources → + → **Browser**. Set the size to **1920 × 1080**. Paste the URL. Leave **Local file** unchecked. `file://` cannot read `current/`, so a local-file browser source will sit there empty.

| Page | URL |
|---|---|
| Lower third, bug, headline, ticker | `http://127.0.0.1:8765/overlay/lower-third.html` |
| Full-screen headline | `http://127.0.0.1:8765/overlay/headline-card.html` |
| Pre-show / countdown | `http://127.0.0.1:8765/overlay/preshow.html` |
| Outro | `http://127.0.0.1:8765/overlay/outro.html` |
| Be right back | `http://127.0.0.1:8765/overlay/brb.html` |

Add `?ticker=0` to the lower-third URL if you would rather scroll `ticker/ticker.txt` yourself as a text source. Add `?headline=0` if the headline is its own text source. Add `?clear=1` on the pre-show or BRB page if you want those pages transparent over your own background.

Create each browser source once. In later scenes, use **Add Existing** and pick the same source. On the source, uncheck **Shutdown source when not visible** and uncheck **Refresh browser when scene becomes active**, or the lower third will flicker on every cut.

If the page shows a red "Cannot read the show files" box, the serve command is not running.

## 3. What each folder is for

| Folder or file | Put it on the stream? | Why |
|---|---|---|
| `current/segment-title.txt` | Yes | Title of the segment you are in. Changes when you hit next. |
| `current/chyron-primary.txt` | Yes | Lower-third top line. |
| `current/chyron-secondary.txt` | Yes | Lower-third second line. |
| `current/chyron.txt` | Optional | Both chyron lines in one file, if you only want one text source. |
| `current/headline.txt` | Yes | The headline you are on. `headline next` advances it. |
| `current/headlines.txt` | Optional | Every headline for this segment, one per line. |
| `ticker/ticker.txt` | Yes | The whole ticker. It does not change until you rebuild. |
| `scenes/show-title.txt`, `scenes/show-subtitle.txt`, `scenes/live-bug.txt` | Yes | Bug / show name. Same all show. |
| `scenes/episode-line.txt`, `scenes/starts-at.txt`, `scenes/account-list.txt` | Yes | Pre-show and outro cards. The account list is only the confirmed social handles. |
| `scenes/call-promo-01.txt` (and `02`, `03`, …), `scenes/call-promos.txt` | Yes, when you ask for topics | Call-in promo lines from `callIns`. One file per line, plus a combined file. |
| `scenes/brb-primary.txt`, `scenes/brb-secondary.txt` | Yes | Be-right-back card. |
| `images/logo/` | Yes | Official logos. Image sources, not text. See the next section. |
| `chyrons/show-host.txt`, `chyrons/show-jess.txt`, and the other `chyrons/show-*.txt` files | Optional | Plates that do not change with the segment. The switcher can also pull these in with `chyron host`, `chyron jess`, `chyron socials`, or `chyron comment`. |
| `chyrons/`, `headlines/`, `segment-titles/` (the numbered files) | No | The library the switcher copies from. Pointing OBS at these means the screen will not follow `next`. |
| `current/segment-meta.txt`, `current/scene-hint.txt`, `current/state.json` | No | Producer info. `scene-hint.txt` is either `host` or `host-jess`. |
| `show-notes/` | No | Generated cue sheet and disclaimer. The spoken rundown is `run-of-show-monday.md` at the repo root. |

There is no jingle file and no camera in this repo. Add those yourself as **Video Capture Device**, **Audio Input Capture**, or **Media Source**. The logos are the only images that ship here.

## 4. Logos

Add an **Image** source (Sources → + → Image) for each logo you actually put on a scene. Create it once, then **Add Existing** on the other scenes. Drag the handles to size it. Do not use Fit to Screen on the bug.

| File | What it is | Where it belongs |
|---|---|---|
| `images/logo/DITM_SunLogo.png` | Full color: black type, yellow sun. Transparent background. | Light backgrounds only. The black type disappears on a dark scene. |
| `images/logo/DITM_SunLogo_White.png` | Same drawing, white type, yellow sun. | Dark backgrounds. Pre-show, countdown, BRB, and outro. |
| `images/logo/ditm_logo_trans_md.png` | White mark on transparent, medium size. | Over video or a color when you want the icon larger than the bug. |
| `images/logo/ditm_logo_bug.png` | Small white corner bug, transparent background. | Top corner of Main Host, Host + Jess, and the full-screen headline. |

The browser pages already place two of these, so you do not add a second copy on a scene that uses the browser source:

- Lower third and headline card: `ditm_logo_bug.png` in the top-right.
- Pre-show, BRB, and outro: `DITM_SunLogo_White.png` centered.

If you skip the browser pages, add the Image sources yourself. A bug about 110–140px tall sits in a corner without covering a face. A full logo about 240px tall, centered, is enough on Pre-show and Outro.

## 5. Build the scenes

Make six scenes. Names below are suggestions. Order in the Scenes panel does not have to match the rundown. You are not building a scene per segment.

Suggested canvas: 1920×1080. Settings → Video.

### Pre-show / Countdown

What the audience sees before 8:00.

- Browser source: the pre-show URL (white full logo, date, start time, accounts). Or, instead, an **Image** source on `images/logo/DITM_SunLogo_White.png` plus text sources reading `scenes/show-subtitle.txt`, `scenes/episode-line.txt`, `scenes/starts-at.txt`, and `scenes/account-list.txt`.
- A dark background or color source. Use `images/logo/DITM_SunLogo.png` only if that background is light.
- A media source for walk-in music or the jingle, if you have the file. This repo does not include audio.
- Leave the camera off, or keep it in the scene and hide the eye icon until you are ready.

There is no countdown clock file. `scenes/starts-at.txt` is the start time from `obs-data.json`. If you want a ticking clock, add an OBS countdown plugin you already use, or just talk over the card.

### Main Host

Drew on camera, lower third, headline, ticker.

- Video Capture Device for the host camera.
- Audio Input Capture for the mic. Confirm it moves in the mixer. Mute desktop audio unless you mean to play the jingle.
- Either the lower-third browser source (it already includes the corner bug), **or** this set of text sources plus an **Image** source on `images/logo/ditm_logo_bug.png` in a top corner:
  - `current/chyron-primary.txt` — large, white
  - `current/chyron-secondary.txt` — smaller, under it
  - `current/headline.txt` — above the lower third
  - `current/segment-title.txt` — small label above the headline
  - `ticker/ticker.txt` — see the scroll filter in step 5
  - `scenes/show-title.txt` and `scenes/live-bug.txt` — corner bug
- A color or image behind the camera only if you want a frame. The browser overlay is transparent; you should see the camera through it.

### Host + Jess

Same sources as Main Host, plus Jess.

- **Add Existing** → the same camera, the same lower third (or the same text sources), the same mic.
- A second Video Capture Device, window capture, or phone source for Jess. Name it so you can find it.
- Cut to this scene when the switcher says `Jess on screen: yes`. That flag is `jessDropIn` in the JSON. `current/scene-hint.txt` will contain `host-jess` (otherwise it contains `host`). The script does not change OBS scenes for you.

### Full-screen headline

A story card with no (or a small) camera.

- Browser source: the headline-card URL (corner bug included). Or one big text source on `current/headline.txt`, with `current/segment-title.txt` as a small kicker above it, plus the bug image.
- Your background under it.
- Optional: a small copy of the show-title bug.

`headline next` in the switcher changes this card, because it reads the same `current/headline.txt` as the lower third.

### BRB

- Browser source: the BRB URL (white logo included). Or the white logo image plus text sources on `scenes/brb-primary.txt` and `scenes/brb-secondary.txt`.
- Music, if you want it, as a media source you can mute from the mixer.

### Outro

Use the outro browser source, or Main Host / Host + Jess with the white full logo (`images/logo/DITM_SunLogo_White.png`) centered. Before you say goodbye, `goto` the last block in `live.py list` (or `next` until you are on it). The sign-off headline and chyrons are whatever that block contains. Then `chyron socials` if you want the social plate, or `chyron call` if you want a call-in plate.

- The outro browser page reads `current/` plus `scenes/account-list.txt`.
- Jingle-out media source, if you have one.

## 6. Ticker scroll

Skip this if the lower-third browser source is showing the ticker.

1. Add a text source, Read from file, file `ticker/ticker.txt`.
2. Font size around 28–36, a wide box along the bottom, height about 50px.
3. Right-click the source → **Filters** → **+** → **Scroll**.
4. Turn on looping if the filter has that checkbox. Horizontal speed is a taste call; start slow enough to read, then raise it.
5. The file is one long line. The build separates items with `•`. It does not change during the show.

## 7. Run the switcher during the show

Open a terminal in this folder before you go live. Leave it open.

```bash
python scripts/live.py reset
python scripts/live.py repl
```

`reset` loads the first block so a rehearsal does not leave you on the closer. The repl prompt shows the block letter and the title of whatever is in `current/`.

| You type | What changes on screen |
|---|---|
| `next` | The next block in the menu, even if it is marked skippable. Title, headline, and chyron all move to that block's first lines. |
| `prev` | The previous block. |
| `goto A` | The block whose letter is A. Letters match the id in `obs-data.json` (`A-…`, `B-…`). Case does not matter. |
| `goto 4` | The block whose **order** is 4. Use the numbers from `list`. `goto` also accepts a full segment id. |
| `skip` | Jump forward to the next block that is not skippable. A signature block is not skippable, so `skip` lands on it instead of jumping over it. If you are already on the last required block, you stay put. |
| `chyron next` / `chyron prev` / `chyron 2` | Another lower third inside this block. `2` means the second chyron. |
| `headline next` / `headline prev` / `headline 2` | Another headline inside this block. |
| `chyron call` | The next call-in promo plate. Run it again to rotate. These plates stay up until you `chyron next` back to the block, or you change blocks. |
| `chyron host` | The show-level host plate. `jess`, `socials`, and `comment` work the same way when those ids exist. A call-in id such as the ones in `callIns.chyrons` works here too. |
| `status` | Print what OBS should be showing, including the Jess flag and any CONFIRM BEFORE AIR note. |
| `list` | Print the menu. |
| `reset` | Back to the first block. |
| `quit` | Leave the repl. OBS keeps showing whatever was written last. |

`next` and `prev` stop at the ends. They do not wrap from the closer back to the open. `goto` is how you leave the suggested order: any letter, any time.

The switcher writes the files and then replaces them. OBS picks up the new timestamp on its own. If a text source sticks, select it, uncheck **Read from file**, check it again.

Changing a block does not change the scene. Stay on Main Host and type `next` or `goto` for a normal block. When `status` says Jess is on screen, click the Host + Jess scene. When that block is over, click back to Main Host.

To read a call-in promo out loud, put a text source on `scenes/call-promo-01.txt` (or the next file) and show it when you ask for topics. Do not announce a phone number or an inbox the segment index still marks CONFIRM BEFORE AIR. `call-ins.md` is the producer note for which routes exist.

`current/segment-meta.txt` repeats the same status, including any "Verify" lines from the JSON. Read it in the terminal, or put that file on a scene you show on a second monitor and never send to the stream.

### Optional hotkeys

OBS cannot run this script from its built-in hotkey page. Two ways to get keys:

1. Leave the repl focused and type the commands. This is the reliable version.
2. Install the free **Advanced Scene Switcher** plugin. Add a macro: condition **Hotkey**, action **Run**. Program `python` (or `python3`), arguments the full path to `scripts/live.py` plus the command, for example `next`. The working directory does not matter.

A second optional macro: if `current/scene-hint.txt` equals `host-jess`, switch to Host + Jess; if it equals `host`, switch to Main Host. Only set that up once the manual cut feels boring. A bad macro will cut the scene while you are mid-sentence.

## 8. Sunday night, before the show

News has to be re-verified Sunday night. The date of the last check is the disclaimer in `obs-data.json`, also written to `show-notes/disclaimer.txt`.

1. Read `run-of-show-monday.md` and `show-notes/segment-index.md`. Leave every **CONFIRM BEFORE AIR** line alone until you have checked it. The same words are in the run of show and, after a build, in the segment index and in `current/segment-meta.txt`. Also read `call-ins.md`, `segues.md`, and `sources.md`. `show-principles.md` is the format. `social-calendar.md` is a draft and is not posted from this folder. `research.md` is background only. The producer studio page is `docs/index.html`.
2. Edit `obs-data.json`. Keep every chyron primary and secondary at or under the max. Do not add a fact you have not just re-checked.
3. If what you will say changed, edit `run-of-show-monday.md` too. Flex blocks can be trimmed or stretched. `skip` only jumps a block the JSON still marks skippable.
4. Run `python scripts/build.py`. Read the count it prints. If it says segments are flagged for verification, open the segment index and clear those before air, or be ready to skip the line.
5. Run `python scripts/live.py list`, then `reset`. Read `current/headline.txt` and `current/chyron.txt` once out loud.
6. Hit **Start Streaming** only after that.

Hand-edited files in `chyrons/`, `headlines/`, `segment-titles/`, `ticker/`, `scenes/`, `current/`, or `playlist.json` will be replaced the next time you build or switch. Edit the JSON.

## 9. When something looks wrong

| What you see | What to do |
|---|---|
| Lower third never changes | The text source is pointed at a file in `chyrons/` or `headlines/` instead of `current/`. Repoint it. |
| Browser source is a black or empty box | Use the `http://127.0.0.1:8765/...` URL. Uncheck **Local file**. Start `python scripts/live.py serve` and leave it running. |
| Red warning on the overlay | Same as above: serve is not running, or the URL is wrong. |
| `·` or `•` looks garbled | Recreate the text source as **Text (FreeType 2)**. The files are UTF-8. |
| Build refuses a chyron | The line is over the max. Shorten it in `obs-data.json`. The script will not cut a news line down for you. |
| `goto` says nothing matches | Run `list` and use the order number in that column, or the segment id from the JSON. |
| You skipped too far | `prev`, or `goto` the order you wanted. `skip` does not delete anything. |
| The open is showing the closer | A rehearsal left the state there. Run `reset` before the real show. |
| A line is stale | Change it in `obs-data.json`, run `build.py`. Re-verify Sunday night rather than editing the `.txt`. |
