# Cold open and jingle

The cold open is ONE flowing paragraph meant to be read aloud quickly (about 45 seconds). `packet/build_packet.py` fills the placeholders from the weekly/daily data file on every build, and shows the result in the studio page (big "Cold open" card with a copy button), the one-page PDF, the txt, the email and `obs-data.json` (`coldOpen`, `jingle`). Edit the templates here and the next build picks them up (the generator reads the fenced blocks under the `TEMPLATE:` and `JINGLE` headings).

## TEMPLATE: MONDAY (show packet)

```text
Good morning, Rio Grande Valley! It's {DAY}, {MONTH} {DATE_ORDINAL}, and you're listening to Drew in the Morning with Drew and Jess. Coming up this hour, the local stories everyone's talking about, starting with {LOCAL_1}, plus {LOCAL_2}. On the National Desk, {NATIONAL_1}. In Trending, {TRENDING_1}. And in How We'd Talk to Our Kids, Jess and I take on {KIDS_TOPIC}. It's {WEATHER_SHORT} outside, the coffee's hot, so stick around, this is Drew in the Morning.
```

## TEMPLATE: DAILY BRIEFING

```text
Good morning, Rio Grande Valley! It's {DAY}, {MONTH} {DATE_ORDINAL}, and this is your Drew in the Morning daily briefing. Today: the local stories everyone's talking about, starting with {LOCAL_1}, plus {LOCAL_2}. On the National Desk, {NATIONAL_1}. In Trending, {TRENDING_1}. And in How We'd Talk to Our Kids, Jess and I take on {KIDS_TOPIC}. It's {WEATHER_SHORT} outside, the coffee's hot, so stick around, this is Drew in the Morning.
```

## JINGLE (primary tagline, spoken over music)

```text
Drew in the Morning. Your Valley, your news, your morning.
```

## JINGLE ALTERNATES

```text
Wake up, RGV. It's Drew in the Morning.
From McAllen to the world, this is Drew in the Morning.
```

## Placeholders

| Placeholder | Filled from | Notes |
|---|---|---|
| `{DAY}` | `meta.date` | Weekday name, for example Monday |
| `{MONTH}` | `meta.date` | Month name, for example November |
| `{DATE_ORDINAL}` | `meta.date` | 23rd, 1st, 2nd, 3rd, 11th and so on |
| `{LOCAL_1}`, `{LOCAL_2}` | `headlines.rgv[].teaser` | Items flagged `"open": true`; if fewer than two are flagged, the first RGV items that have a `teaser`; fallback is the trimmed `short` title. Spoken style, 12 words or fewer |
| `{NATIONAL_1}` | `nationalDesk[].teaser` | First story with a teaser (fallback: trimmed title) |
| `{TRENDING_1}` | `trending[].teaser` | First trending item flagged `print`/with a teaser (fallback: trimmed title) |
| `{KIDS_TOPIC}` | `meta.kidsTopic` | Topic for "How We'd Talk to Our Kids". If it is missing (usual on daily briefings) the whole sentence is dropped |
| `{WEATHER_SHORT}` | NWS data | For example "75 and a chance of rain showers": the show-day forecast high and the forecast condition. On a daily build dated today it uses the current KMFE reading |

Rules:

- Any sentence that still has an unfilled placeholder is dropped, so the paragraph never reads "{TRENDING_1}" on air.
- CONFIRM markers are stripped from spoken text. If a teased item is unconfirmed (`confirm` set or `verified: false`), a small "CONFIRM BEFORE AIR" note listing it is shown under the paragraph on the studio page and in the txt. The note is never part of the spoken text.
- There is no phone number in the cold open. Listener contact is DMs and ditm@drewlentz.com (CONFIRM BEFORE AIR that it is public).

## Jingle usage

- Primary: read or sing over the jingle bed right before the cold open and again at the show close.
- Alternates: rotate by weekday if you want some variety.
- The build writes the filled paragraph and the jingle lines to `obs-data.json` under `coldOpen` and `jingle`, so OBS or Bitfocus Companion can show them as text sources.
