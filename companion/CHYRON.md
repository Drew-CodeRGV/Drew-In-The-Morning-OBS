# DITM news chyron (OBS browser source)

`docs/chyron.html` (live: https://ros.drewinthemorning.com/chyron.html) is a 1920x1080 transparent lower third:
navy-to-accent gradient bar, DITM logo bug on the left, small type (headline ~38px, line ~27px), slide/fade changes.
No segment title, no block letter. It is rebuilt from `obs-data.json` by `companion/chyron_build.py`
(called from `companion/build_companion.py` and `packet/build_packet.py`, so the daily refresh keeps it current),
which also writes `docs/chyron.json` (the page re-reads it when served over http).

## Control: commands only
`start stop hold resume toggle next prev goto{idx} clear show`. Nothing else is accepted, no free text.

1. **obs-browser event** (Stream Deck / Companion): obs-websocket `CallVendorRequest`, vendorName `obs-browser`,
   requestType `emit_event`, requestData `{"event_name":"ditm","event_data":{"cmd":"goto","idx":3}}`.
2. **ntfy.sh topic** (iPad dashboard): the page listens on `?topic=<topic>` over EventSource and publishes its
   state (`k:"state"`) back so the dashboard can show HELD / current block.

The topic is a random secret kept OUT of this public repo: pass it as `chyron.html?topic=...` in the OBS source and
as `?ctl=...` once on the run-of-show dashboard (saved on that iPad, then removed from the address bar).
Without a topic the page still works from the obs-browser event.

## Auto-advance
Dashboard **Start** publishes `start`; the chyron then follows the run-of-show timing (block offsets in `obs-data.json`,
60 min) and the dashboard mirrors the chyron's block/held state. **Hold** freezes the topic and the show clock;
**Resume** carries on and every later topic moves back by the time held. Prev/Next/Goto re-time the show to that block.
Reset on the dashboard publishes `stop`. A reloaded browser source resumes the show state but comes back off air.

## Tests
`tools/ui_test_chyron.js <docs/chyron.html> <studio.html>` (puppeteer, mock ntfy server), `tests/test_chyron.py`.
