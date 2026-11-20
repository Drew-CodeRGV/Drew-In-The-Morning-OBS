# Stream Deck for Drew in the Morning

Bitfocus Companion on the same Ubuntu machine as OBS. One key per show block. The words and colors come from `obs-data.json`. Scene names come from `OBS-setup.md`.

This is a generator, not a config that was exported from a running Companion. Read the import section before you load the file.

## 1. Install Companion

Download the Linux build from the official page, [bitfocus.io/companion/download](https://bitfocus.io/companion/download), or from the [GitHub releases](https://github.com/bitfocus/companion/releases). Pick the x64 build that matches Companion 3.x or 4.x. The filename changes with the version, so use the name on the page you downloaded.

If the release includes a `.deb`:

```bash
sudo apt install ./companion-linux-x64-*.deb
```

If it includes a `.tar.gz` instead (this is the build most releases ship):

```bash
tar -xzf companion-linux-x64-*.tar.gz
cd companion
./companion
```

The admin UI is usually at `http://127.0.0.1:8000`. If that page does not load, check the terminal Companion printed. The port can be changed in its config. Confirm the port on your version.

An official Flatpak was not confirmed for this guide. Use the Bitfocus `.deb` or `.tar.gz`.

### Stream Deck USB access

Companion ships a udev rules file named `50-companion.rules`. After you unpack or install, find it:

```bash
find . /opt /usr -name '50-companion.rules' 2>/dev/null
```

Copy that file. Do not write your own rules.

```bash
sudo cp /path/to/50-companion.rules /etc/udev/rules.d/50-companion.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug the Stream Deck and plug it back in. If it still does not appear, log out and back in so your session picks up the device permissions.

### Start it with the session

A template unit is `companion/companion-user.service`. Point `ExecStart` at the real binary (the tarball's `companion` file, or the path the `.deb` installed). Then:

```bash
mkdir -p ~/.config/systemd/user
cp companion/companion-user.service ~/.config/systemd/user/companion.service
# edit ExecStart first
systemctl --user daemon-reload
systemctl --user enable --now companion.service
```

`systemctl --user` only runs while you are logged in, unless you also enable lingering (`sudo loginctl enable-linger "$USER"`). Lingering is optional. If you would rather not use systemd, start `./companion` from a terminal or add that command to your desktop's autostart list. The autostart dialog differs by desktop, so use the one Ubuntu Settings shows for your session.

## 2. Turn on OBS WebSocket

OBS 28 and later includes the WebSocket server.

1. OBS menu **Tools → WebSocket Server Settings**.
2. Enable the server.
3. Leave the port at **4455** unless you have a reason to change it.
4. Set a password. Keep it in OBS and in Companion. Do not put it in this repo.
5. **Show Connect Info** is the place that displays the host, port, and password. The button label can vary. If you do not see it, check your OBS version.

If **Tools** has no WebSocket item, the install is older than OBS 28, or the websocket build was disabled. This guide does not cover the old obs-websocket 4.x plugin.

## 3. Connect Companion to OBS

On the Connections page (Companion 3.x and 4.x both have this; some builds still say Instances):

1. Add a connection.
2. Search for **OBS Studio** (`obs-studio`).
3. Host `127.0.0.1`, port `4455`, and the password from step 2.
4. Save. The connection should go green while OBS is open.

The generated file also adds this connection with an **empty password**, so an import does not smuggle a secret. Type the real password in the connection after import.

## 4. Build and import

From the repo root, after any change to `obs-data.json`:

```bash
python3 companion/build_companion.py
```

That rewrites:

| File | What it is |
|---|---|
| `ditm-showblocks.companionconfig` | Full-config JSON Companion can try to import |
| `blocks.json` | The 12 blocks, colors, and the text each key sends |
| `custom-variables.json` | The same variables, if you add them by hand |
| `obs-websocket-requests.json` | Raw OBS WebSocket v5 requests |
| `button-table.md` | The manual layout, if import fails |

### How sure the import format is

Fairly sure about the envelope, not sure the buttons will import untouched.

Companion's public export code (`ImportExport/Export.ts` and `ExportModel.ts` on the default branch) writes a JSON document with `type: "full"` and a `version`. As of that tree, `FILE_VERSION` is **12**, and the type allows versions **6 through 13**. A file newer than the running app is rejected with "saved with a newer unsupported version."

This generator writes **version 6**, which is the Companion 3.5-era export, so a current Companion can upgrade it on the way in. It was **not** produced by Companion's Export button. Button steps still use the older `steps.action_sets` shape (`instance`, `action`, `options`), and the OBS connection sets both `moduleId` and `instance_type` to `obs-studio` because those names changed across 3.x and 4.x.

Import it from Companion's import page as a **full** config. Full import replaces the config you have. Export a backup first.

If the import errors, or the buttons come in empty, or an action says the id is unknown, stop using the file and build the page from `button-table.md` plus `custom-variables.json`. The action names to pick in the UI are **Set Source Text**, **Set Program Scene** (wording may be "Set Current Scene"; check your module version), and **Set Source Visibility**.

Action ids written into the file, which you should confirm after import:

| Id | Intended module action |
|---|---|
| `set_text` | Set Source Text. Options `source` and `text`. |
| `set_current_scene` | Set the program scene. Option `scene`. |
| `set_source_visibility` | Show the lower third. Options `scene`, `source`, `visible`. |
| `custom_variable_set_value` | Internal: set a custom variable. |
| `custom_variable_set_expression` | Internal: set a custom variable from an expression. |

If your module uses different option names, the button table still has the text to paste.

### Button layout

15-key Stream Deck (5 columns by 3 rows), aligned to the top-left of Companion page 1:

| | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Row 0 | A | B | C | D | E |
| Row 1 | F | G | H | I | J |
| Row 2 | K | L | (empty) | PREV | NEXT |

Each block key is filled with that block's `color` from `obs-data.json` and labeled with the letter plus a short name (`shortName` from `obs-data.json`, else the words of the title before a colon, trimmed so they fit).

PREV and NEXT wrap. From L, NEXT lands on A. From A, PREV lands on L. The expression is `($(internal:custom_ditm_block_index) + 1) % 12` and `(... + 11) % 12`.

32-key XL (8 by 4) shows two more keys on the same page:

- Row 0, column 5: status. The label is `$(internal:custom_ditm_block)` and `$(internal:custom_ditm_title)`. Some Companion versions want `$(custom:ditm_block)` instead. If the key shows the variable name literally, switch to the other form.
- Row 0, column 6: CLEAR. Empties the four text sources. It does not change the block index.

A 15-key deck cannot see columns 5 and 6. Use the on-screen emulator (Companion's web UI has one; where the button sits depends on the version) or move those two keys to page 2.

The active block key has a feedback that turns the key white when `internal:custom_ditm_block_index` equals that key. Feedback import is the least certain part. If nothing highlights, add it in the UI: feedback **variable value**, variable `internal:custom_ditm_block_index`, equals the key's index.

## 5. OBS sources these keys expect

Create these on the **Drew in the Morning** scene. Names must match.

| Source | Type | Read from file |
|---|---|---|
| `DITM Chyron` | Text (FreeType 2) | Off |
| `DITM Headline` | Text (FreeType 2) | Off |
| `DITM Segment Title` | Text (FreeType 2) | Off |
| `DITM Block Letter` | Text (FreeType 2) | Off |
| `DITM Block Card` | Image | Optional. No card art ships in this repo, so leave it out until you have files. |
| `DITM Lower Third` | The browser source, or a group around it | Optional. The keys try to enable this item on the Drew in the Morning scene. |

Leave **Read from file** off on the four text sources. If it is on, OBS keeps the file and ignores `SetInputSettings`. The file-based sources in the rest of this repo (`current/chyron-primary.txt` and the others) are the path the Python switcher uses. The Stream Deck writes the `DITM …` sources directly. Use one path or the other for a given line, not both, or they will fight.

Block keys also switch the program scene to **Drew in the Morning** (the only scene the show uses; `jessDropIn` no longer changes the scene). Those scene names are the ones in `OBS-setup.md`. Rename either the scenes or `SCENE_HOST` / `SCENE_JESS` in `build_companion.py` if yours differ, then rebuild.

Each press sends the block's **first** chyron (primary, then secondary, each already checked to be 60 characters or fewer) and the **first** headline.

### Raw OBS WebSocket v5

`obs-websocket-requests.json` is the same press as JSON, without Companion. `overlay: true` keeps the font. A text change:

```json
{
  "requestType": "SetInputSettings",
  "requestData": {
    "inputName": "DITM Chyron",
    "inputSettings": {"text": "line one\nline two"},
    "overlay": true
  }
}
```

A scene change:

```json
{"requestType": "SetCurrentProgramScene", "requestData": {"sceneName": "Drew in the Morning"}}
```

Showing the lower third needs the numeric item id from `GetSceneItemId`, then:

```json
{
  "requestType": "SetSceneItemEnabled",
  "requestData": {"sceneName": "Drew in the Morning", "sceneItemId": 0, "sceneItemEnabled": true}
}
```

`sceneItemId: 0` in that example is a placeholder. Read the real id first.

OSC is only a fallback if you already run the **obs-osc** plugin. This page does not speak OSC. The requests above are the WebSocket equivalents of what an OSC route would have to do.

## 6. Dry run without Companion

```bash
pip install obsws-python
python3 companion/obs-websocket-test.py --list
OBS_WEBSOCKET_PASSWORD='the-password-from-obs' python3 companion/obs-websocket-test.py --index 0
OBS_WEBSOCKET_PASSWORD='the-password-from-obs' python3 companion/obs-websocket-test.py --cycle --dwell 1
```

`--lower-third` also enables `DITM Lower Third`. Leave it off until that source exists. The password stays in the environment, not in a file.

## 7. When the rundown changes

```bash
python3 scripts/build.py
python3 companion/build_companion.py
```

Re-import, or update the keys from the new `button-table.md`. Import replaces the whole Companion config, so re-enter the OBS password afterward.

## 8. Troubleshooting

| What you see | What to try |
|---|---|
| Stream Deck never appears | Confirm `50-companion.rules` is in `/etc/udev/rules.d`, reload udev, replug, and log out once. `lsusb` should show Elgato (`0fd9`). |
| Companion UI does not load | Confirm the process is running and try `http://127.0.0.1:8000`. Check the port in the log. |
| OBS connection stays red | OBS is open, the websocket server is enabled, port 4455, password matches, host is `127.0.0.1`. |
| Import says the file is too new or corrupt | Use `button-table.md`. Do not hand-edit the version number upward. |
| A button imports but the action is blank | The action id did not match your module. Recreate it with Set Source Text / Set Program Scene. The table has the strings. |
| Text on air does not change | The source name does not match, or Read from file is on. |
| PREV/NEXT changes the key but not the picture | The expression action did not run, or the OBS actions fired before the variables updated. Select the button and confirm the delays (30 ms on the expressions, 80 ms on the text). |
| The active key does not light | Add the variable feedback by hand. That part of the import is the one most likely to be dropped. |
| Middle dots look wrong | Use Text (FreeType 2), same as the rest of the show. |
| Keys cut to the wrong scene | Your scene is not named `Drew in the Morning`. |
