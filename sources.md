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

## Email newsletters (Drew's Gmail, READ-ONLY through the Gmail connector)
- **Fast Company Daily** (what's-happening-in-tech section, block J "Tech" sub-segment). Looked up each morning in drew@drewlentz.com first, then drew@politiquera.com (and Outlook if connected): search `(from:fastcompany OR subject:"Fast Company Daily") newer_than:2d`, read the newest issue, take 3 to 5 stories with the link from the email.
- Status on Nov 19, 2026, 6:25 AM CT: **no Fast Company Daily issue found** in either Gmail account or Outlook (searched `fastcompany`, "Fast Company", the subject, spam/trash included). The only Fast Company mail is Premium subscription receipts from subscriptions@fastcompany.com / care@fastcompany.com (newest Oct 24, 2023). Drew needs to confirm he is subscribed at https://www.fastcompany.com/newsletters (that page bot-blocks the box, so open it in a browser) and which address it goes to. Until an issue arrives the section uses the tech wires and says FALLBACK.
- Fallback tech wires (no login, RSS verified 2026-11-19): The Verge https://www.theverge.com/rss/index.xml · TechCrunch https://techcrunch.com/feed/ · Ars Technica https://feeds.arstechnica.com/arstechnica/index (listed under `tech_feeds` in feeds.yml; `python3 tools/tech_wires.py --text` lists the last 48 hours). Fast Company's own website feed https://www.fastcompany.com/latest/rss exists but is disabled: it is not the Daily.
