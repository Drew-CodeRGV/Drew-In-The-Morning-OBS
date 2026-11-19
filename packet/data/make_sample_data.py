#!/usr/bin/env python3
"""Writes data/packet-2026-11-23.json (the SAMPLE content file). A weekly run copies this shape.
Every item carries a url; items without one are flagged CONFIRM BEFORE AIR by build_packet.py."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
def L(label, url): return {"label": label, "url": url}
def it(title, short, url, source, **k):
    d = {"title": title, "short": short, "url": url, "source": source}; d.update(k); return d

data = {
 "meta": {
  "date": "2026-11-23", "dateLabel": "Monday, November 23, 2026", "title": "Drew in the Morning · Monday Show Packet",
  "tagline": "Drew & Jess are watching the feeds so you don't have to",
  "sample": True, "sampleLabel": "SAMPLE / preview, data as of Nov 18",
  "dataAsOf": "Nov 18, 2026, 8:15 PM CT", "timezone": "America/Chicago",
  "recap": "Week of Nov 11-18 and the weekend of Nov 14-15",
  "showEmail": "ditm@drewlentz.com", "showEmailConfirm": True,
  "handles": "IG/TikTok @drewinthemorning · YouTube @DrewintheMorning"
 },
 "headlines": {
  "image": {"file": "assets/starship_thumb.jpg", "caption": "File photo: Starship (Steve Jurvetson, CC BY 2.0, Wikimedia Commons)", "credit_url": "https://commons.wikimedia.org/wiki/File:SpaceX_Starship_before_IFT-5.jpg", "forItem": 0},
  "rgv": [
   it("Cameron County rejects SpaceX data-center tax break hearing, 3-2", "County says no to SpaceX's 10-yr, 100% tax break hearing (3-2)", "https://myrgv.com/local-news/2026/11/17/cameron-county-commissioners-reject-spacex-bid-for-data-center-tax-break/", "MyRGV · Nov 17"),
   it("Texas issues air permit for SpaceX's $24B data center", "State air permit issued Nov 16 after Abbott's Sept pause", "https://www.politico.com/news/2026/11/17/texas-issues-air-permit-for-massive-spacex-data-center-01170758", "Politico · Nov 17"),
   it("Starship Flight 15: ship caught by tower, booster aborts catch", "Flight 15: ship caught by tower Nov 14; booster aborted", "https://spaceflightnow.com/2026/11/13/live-coverage-starship-flight-15-attempts-to-recover-full-vehicle-in-double-launch-pad-catch/", "Spaceflight Now · Nov 13"),
   it("Mission mayor and council races head to Dec. 12 runoffs", "Mission mayor, council races go to Dec 12 runoffs", "https://www.krgv.com/news/mission-mayoral-and-city-council-runoff-elections-set-for-dec-12/", "KRGV"),
   it("Texas A&M McAllen to build $50M health education building", "Texas A&M McAllen: $50M health building, starts Dec", "https://dailymcallen.com/local-news/editions/11-18-2026", "Daily McAllen · Nov 18"),
   it("McAllen Food Truck Park closure delayed to Jan. 14, 2027", "Food Truck Park closure moved to Jan 14, 2027", "https://dailymcallen.com/local-news/editions/11-17-2026", "Daily McAllen · Nov 17"),
   it("Another screwworm case confirmed in Starr County cattle", "USDA: another screwworm case in Starr County", "https://thergvnews.com/reviews/day/2026-11-17", "The RGV News · Nov 17"),
   it("Pharr twin bridge expansion opened Nov. 13", "Pharr International Bridge twin span opened Nov 13", "https://gooddayedinburg.com/local-news/editions/11-14-2026", "Good Day Edinburg · Nov 14"),
   it("Grupo Frontera, Edgar Barrera win at Latin Grammys", "Edinburg's Grupo Frontera wins at Latin Grammys", "https://gooddayedinburg.com/local-news/editions/11-14-2026", "Good Day Edinburg · Nov 14"),
   it("PSJA ISD swears in three trustees, elects Quintanilla president", "PSJA ISD swears in 3 trustees", "https://www.psjaisd.us/school-news-details/~board/pharr-san-juan-alamo-isd-news/post/psja-isd-swears-in-three-trustees-elects-new-board-leadership", "PSJA ISD · Nov 16")
  ],
  "texas": [
   it("Congress Democrats ask DHS inspector general to probe ~$7.5B Big Bend border contracts", "Democrats ask for probe of ~$7.5B Big Bend border contracts", "https://texianpartisan.com/news/daily-briefing/daily-briefing-tuesday-november-17-2026/", "Texian Partisan · Nov 17"),
   it("Texas Supreme Court petition over HD 93 special election result", "Texas Supreme Court petition over HD 93 special election", "https://texianpartisan.com/news/daily-briefing/daily-briefing-tuesday-november-17-2026/", "Texian Partisan · Nov 17"),
   it("PUC takes up Aqua Texas rate increase Thursday", "PUC takes up Aqua Texas rate hike Thursday (Nov 19)", "https://texianpartisan.com/news/daily-briefing/daily-briefing-tuesday-november-17-2026/", "Texian Partisan · Nov 17")
  ]
 },
 "nationalDesk": [
  {"id": "faa", "title": "FAA nationwide ground stop", "print": True,
   "summary": "Nov 13: FAA grounded all U.S. flights ~3:30-8:15 PM ET; legacy network overwhelmed by data; FAA sees no cyberattack.",
   "angle": "Everybody wants the system modernized; nobody wants it down for the upgrade.",
   "valley": "HRL, MFE and BRO issued advisories; Brownsville still had 5 cancellations that night.",
   "detail": "FAA: legacy equipment became unstable when data flooded its FTI network; suspected sites a radar site in Amarillo and a radio site in El Dorado, AR where L3Harris was deploying a router; 17 of 22 en route centers affected; ~3,500 aircraft landed safely; ~12,462 flights canceled that day. Second nationwide ground stop since 9/11 (ABC). FAA Administrator Bryan Bedford told Congress Nov 18: 'blame me.' Duffy said the issue came on the 69th router installation. Harlingen: incoming banks from IAH/DFW/AUS couldn't depart. No current FAA flight cuts found in the sources checked.",
   "links": [L("FAA: Nationwide Ground Stop Q&A", "https://www.faa.gov/newsroom/nationwide-ground-stop-questions-and-answers"), L("ABC: FAA head says 'blame me'", "https://abcnews.com/Politics/mullin-faces-congressional-hearing-wake-historic-nationwide-ground/story?id=138226960"), L("ValleyCentral: Valley airports issue advisories", "https://www.valleycentral.com/news/local-news/valley-airports-airports-issue-travel-advisories-amid-faa-nationwide-ground-stop/amp/"), L("KRGV: Brownsville airport after ground stop", "https://www.krgv.com/news/cancellations-and-delays-linger-at-brownsville-airport-after-nationwide-faa-ground-stop-ends/")],
   "confirm": ["Any current FAA flight cuts (none found)"]},
  {"id": "mullin", "title": "Mullin testifies on outages and the LSU-Texas flight", "print": True,
   "summary": "DHS Sec. Markwayne Mullin told House Homeland Security (Nov 18) the outages weren't a coordinated attack; defended flying to the LSU-Texas game.",
   "angle": "Fair question or cheap shot? The optics of flying to a game during a grounding are rough.",
   "valley": "DHS runs the border; ask what RGV ranchers, bridges and Border Patrol are actually seeing.",
   "detail": "Hearing: 'Worldwide Threats to the Homeland: 25 Years After 9/11,' with DNI Jay Clayton and FBI Deputy Director Christopher Raia. Clayton: 'separate service outages associated with maintenance and technical changes,' not a coordinated or state-sponsored attack. Mullin said he wanted to be a good uncle and will reimburse the government; he was also pressed on ICE training. His written testimony says Southwest border apprehensions fell 58% in FY2026 (DHS's claim).",
   "links": [L("ABC: Mullin grilled, FAA head says 'blame me'", "https://abcnews.com/Politics/mullin-faces-congressional-hearing-wake-historic-nationwide-ground/story?id=138226960"), L("AP: Takeaways from Mullin's testimony", "https://apnews.com/article/mullin-congress-ground-stop-cyber-threats-immigration-ce63a22797c61ee53d88678000236c37"), L("PBS: Mullin defends flight to football game", "https://www.pbs.org/newshour/politics/watch-live-dhs-secretary-mullin-testifies-on-worldwide-threats-amid-tech-outages-iran-warnings"), L("House Homeland Security: Mullin written testimony (PDF)", "https://homeland.house.gov/wp-content/uploads/2026/11/2026-11-18-HRG-Testimony-Mullin.pdf")],
   "confirm": ["Drew said 'Mullen': this is Sec. Markwayne Mullin (confirm with Drew)"]},
  {"id": "snl", "title": "SNL: Mulaney, Bridgers and the 'Sister' sketch", "print": True,
   "summary": "Nov 14: John Mulaney hosted (7th time), Phoebe Bridgers sang; 'CIA Meeting' cold open roasted tech CEOs; critics called it the season's best.",
   "angle": "A cold open that skips politics and still lands. 'Sister' hit people in the gut.",
   "valley": "The cold open roasted the same ground stop that sent HRL, MFE and BRO advisories.",
   "detail": "Cold open: Mulaney as a CIA officer lecturing Musk, Altman, Thiel, Zuckerberg and Amodei about honey-trap spies after the Jensen Huang scandal; Bowen Yang returned as Huang. Also: 'Sister,' 'Plane Crash,' 'Gettin' It Done,' 'Woodstock,' 'Kathy,' and a Central Park carriage ride musical sketch. Bridgers: 'Bobby' and 'Still Standing.' Reaction: EW 'easily the best episode of this season'; Boston.com 'far and away the best'; ratings 4.45M, down 20% from the prior week (Showbiz411). The 'Sister' video: a pretaped fake elder-care testimonial ad (Jane Wickline as the sister), SNL's YouTube channel, published Nov 14, 2:59, ~5.8M views when checked Nov 18. Last new episode before Thanksgiving; next is in December (Amanda Seyfried, per EW).",
   "links": [L("YouTube: SNL 'Sister' (the sister video)", "https://www.youtube.com/watch?v=-X9dxL17t1k"), L("YouTube: SNL 'CIA Meeting' cold open", "https://www.youtube.com/watch?v=R_8UPhJNrZ4"), L("EW: SNL recap", "https://ew.com/snl-recap-john-mulaney-hosts-seventh-time-phoebe-bridgers-musical-guest-12253185"), L("Boston.com: SNL recap", "https://www.boston.com/culture/entertainment/2026/11/15/snl-recap-john-mulaney-2026/"), L("Showbiz411: ratings", "https://www.showbiz411.com/2026/11/18/john-mulaney-phoebe-bridgers-snl-best-this-season-drops-back-to-season-average-ratings-down-20-from-last-weeks-high"), L("NBC Insider: monologue and sketches", "https://www.nbc.com/nbc-insider/watch-john-mulaney-november-14-snl-monologue-sketches")],
   "confirm": ["'Sister' = the sister video Drew meant (confirm with Drew)"]},
  {"id": "huang", "title": "Nvidia's Jensen Huang resigns", "print": False,
   "summary": "Nov 12: Nvidia said Huang resigned as CEO and board member effective immediately; CFO Colette Kress is interim CEO.",
   "angle": "The AI boom's biggest face is gone, and Nvidia chips still power every data center.",
   "valley": "Starbase's $24B data center is exactly that kind of AI compute fight.",
   "detail": "Source for the resignation facts is Nvidia's own press release. Mainstream reports link it to an alleged affair with a suspected Chinese spy (the SNL cold open built on it); verify allegation details through a reported source before characterizing them.",
   "links": [L("Nvidia press release: CEO transition", "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-CEO-Transition/default.aspx")],
   "confirm": ["Allegation details (not independently verified here)"]},
  {"id": "tencom", "title": "Texas Ten Commandments law in doubt", "print": True,
   "summary": "ABC (Nov 18): Democratic midterm wins put Texas's classroom Ten Commandments mandate in doubt; the law still stands.",
   "angle": "Whatever you think of it, parents deserve a straight answer on what's on the classroom wall.",
   "valley": "It applies in every RGV school; ask what your child's classroom has up.",
   "detail": "ABC reports legal battles over classroom displays are headed toward the Supreme Court. The law remains in effect unless courts or lawmakers change it. Verify details of repeal efforts before airing.",
   "links": [L("ABC: Democratic wave upends Ten Commandments battle in Texas classrooms", "https://abcnews.com/Politics/democratic-wave-upends-battle-ten-commandments-texas-classrooms/story?id=138118010")],
   "confirm": ["Details of any repeal bill (verify)"]}
 ],
 "weather": {"mode": "nws", "lat": 26.2034, "lon": -98.23, "note": "McAllen / Rio Grande Valley; NWS Brownsville (BRO) forecast"},
 "sports": {
  "highSchool": {
   "title": "RGV High School Football Playoffs", "round": "Bi-District results (Nov 12-14); Area round this week",
   "sourceNote": "RGVSports.com scoreboard (updated Nov 18); Daily McAllen Nov 14; KRGV",
   "results": [
    it("PSJA North 64, Edinburg 10 (6A-II)", "PSJA North 64, Edinburg 10", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Weslaco 43, Los Fresnos 3 (6A-I)", "Weslaco 43, Los Fresnos 3", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Harlingen 51, La Joya 50 (6A-I)", "Harlingen 51, La Joya 50", "https://rgvsports.com/mercedes-outlasts-mission-veterans-in-exciting-clash-bi-district-roundup/", "RGVSports"),
    it("Edinburg Vela 42, Brownsville Veterans 20 (6A-II)", "Vela 42, Brownsville Vets 20", "https://rgvsports.com/mercedes-outlasts-mission-veterans-in-exciting-clash-bi-district-roundup/", "RGVSports"),
    it("McAllen High 62, Weslaco East 19 (5A-I)", "McAllen 62, Weslaco East 19", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("McAllen Rowe 44, Flour Bluff 28 (5A-I)", "McAllen Rowe 44, Flour Bluff 28", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports", confirm="Opponent changed on RGVSports Nov 18 (earlier listing said Sharyland High); CONFIRM BEFORE AIR"),
    it("Mercedes 44, Mission Veterans 42 (5A-II)", "Mercedes 44, Mission Vets 42", "https://rgvsports.com/mercedes-outlasts-mission-veterans-in-exciting-clash-bi-district-roundup/", "RGVSports"),
    it("Sharyland 31, Brownsville Pace 20 (5A-II)", "Sharyland 31, Brownsville Pace 20", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("CC Veterans 59, McAllen Memorial 23 (5A-I)", "CC Vets 59, McAllen Memorial 23", "https://dailymcallen.com/local-news/editions/11-14-2026", "Daily McAllen / KRIS 6"),
    it("CC Carroll 48, La Joya Palmview 17 (5A-I)", "CC Carroll 48, Palmview 17", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Gregory-Portland 68, Sharyland Pioneer 16 (5A-II)", "Gregory-Portland 68, Pioneer 16", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Calallen 64, Hidalgo 0 (4A-I)", "Calallen 64, Hidalgo 0", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Port Lavaca Calhoun 17, Edcouch-Elsa 3 (4A-I)", "Calhoun 17, Edcouch-Elsa 3", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Orange Grove 35, Raymondville 28 (3A-I)", "Orange Grove 35, Raymondville 28", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("La Villa 67, Pettus 0 (2A-II)", "La Villa 67, Pettus 0", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports")
   ],
   "next": [
    it("Thu Nov 19: Weslaco at SA Brennan 6 PM; McAllen vs Boerne Champion 7 PM (Laredo); Mercedes vs Boerne 7 PM (Laredo); Sharyland vs Alamo Heights 7 PM (Corpus Christi)", "Thu: Weslaco @ SA Brennan 6; McAllen v Boerne Champion 7; Mercedes v Boerne 7; Sharyland v Alamo Heights 7", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Fri Nov 20: Harlingen vs SA Harlan 7 PM; PSJA North vs SA Warren 7 PM (Alice); McAllen Rowe vs Smithson Valley 7 PM; La Villa vs Chilton 7 PM", "Fri: Harlingen v SA Harlan; PSJA North v SA Warren; Rowe v Smithson Valley; La Villa v Chilton (all 7)", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports"),
    it("Sat Nov 21: SA Sotomayor at Edinburg Vela 3 PM", "Sat: SA Sotomayor @ Vela 3 PM", "https://rgvsports.com/rgv-football-playoff-schedule/", "RGVSports")
   ],
   "note": "Area-round results will be in the real Monday packet. College: Stephen F. Austin 48, UTRGV 0 (Nov 14).",
   "college": it("UTRGV falls 48-0 to No. 7 SFA in the home finale (UTRGV 5-6)", "UTRGV 0, Stephen F. Austin 48 (Nov 14)", "https://gooddayedinburg.com/local-news/editions/11-15-2026", "Good Day Edinburg / CBS Sports")
  },
  "nfl": {
   "title": "NFL Week 10", "scoreSource": it("NFL.com scores, Week 10", "", "https://www.nfl.com/schedules/2026/by-week/week-10", "NFL.com"),
   "scores": [
    ["Thu Nov 12", "WAS 24, NYG 21"], ["Sun Nov 15", "DET 35, NE 10 (Munich)"], ["Sun Nov 15", "KC 35, ATL 13"], ["Sun Nov 15", "CLE 27, HOU 24"],
    ["Sun Nov 15", "MIN 30, GB 10"], ["Sun Nov 15", "IND 24, MIA 22"], ["Sun Nov 15", "CAR 20, NO 17"], ["Sun Nov 15", "BUF 31, NYJ 12"],
    ["Sun Nov 15", "JAX 40, TEN 23"], ["Sun Nov 15", "LAR 34, ARI 6"], ["Sun Nov 15", "SEA 21, LV 13"], ["Sun Nov 15", "SF 46, DAL 40"],
    ["Sun Nov 15", "CIN 38, PIT 18 (SNF)"], ["Mon Nov 16", "LAC 23, BAL 20 (MNF)"]
   ],
   "notable": [
    it("Burrow threw for 409 and Chase had 231 receiving yards in Cincinnati's 38-18 win over Pittsburgh", "Burrow 409 yds, Chase 231 yds in CIN 38-18 win", "https://www.pro-football-reference.com/years/2026/week_10.htm", "Pro-Football-Reference"),
    it("49ers beat the Cowboys 46-40 (Purdy 389 yds); SF and BUF lead at 8-1; Cowboys 4-6, Texans 3-6", "SF 46-40 over Dallas; Cowboys 4-6, Texans 3-6", "https://www.nfl.com/schedules/2026/by-week/week-10", "NFL.com / PFR"),
    it("Week 11: Colts at Texans Thu Nov 19; Titans at Cowboys Sun Nov 22; Bengals at Commanders Mon Nov 23", "Week 11: Colts @ Texans Thu; Titans @ Cowboys Sun; Bengals @ Commanders Mon", "https://www.footballdb.com/games/index.html?yr=2026", "FootballDB schedule")
   ]
  },
  "nba": {
   "title": "NBA", "scoreSource": it("Basketball-Reference: Nov 17 scores", "", "https://www.basketball-reference.com/boxscores/", "Basketball-Reference"),
   "scores": [["Tue Nov 17", "NYK 111, TOR 102"], ["Tue Nov 17", "MIN 106, POR 105"], ["Tue Nov 17", "DET 105, SAS 93"], ["Tue Nov 17", "UTA 132, LAC 107"], ["Tue Nov 17", "LAL 118, CHA 114 (OT)"]],
   "texas": [["Mon Nov 16", "MIA 128, HOU 110"], ["Sun Nov 15", "BOS 131, DAL 94"]],
   "notable": [
    it("Lakers (13-2) have won nine straight; Quentin Grimes scored 47 in the OT win over Charlotte", "Lakers 13-2, nine straight; Grimes 47 in OT win", "https://buzzerbeaternews.com/news/nba-scores-last-night-2026-11-17/", "Buzzer Beater News"),
    it("Spurs are 12-3 despite the loss to Detroit; Magic snapped Boston's six-game win streak Monday", "Spurs 12-3; Magic snapped Celtics' 6-game streak", "https://www.nba.com/news/starting-5-november-17-2026", "NBA.com"),
    it("Texas teams: Rockets lost at Miami 128-110 (Nov 16); Mavericks lost at Boston 131-94 (Nov 15)", "Rockets lost at MIA 128-110; Mavs lost at BOS 131-94", "https://statsnext.com/nba/games/2026-11", "StatsNext")
   ]
  },
  "mlb": {
   "title": "MLB: OFFSEASON (no scores)", "offseason": True,
   "note": "MLB is in the offseason in November, so this card shows news instead of scores. The Brewers are 2026 World Series champions.",
   "notable": [
    it("Skubal sweepstakes: Mets, Blue Jays, Dodgers and Padres have met or are set to meet; a deal is expected before the CBA expires Dec. 1 (11:59 PM ET)", "Skubal talks: Mets, Jays, Dodgers, Padres; deal expected before CBA expires Dec 1", "https://www.mlb.com/news/tarik-skubal-rumors-november-17-free-agent-update", "MLB.com"),
    it("Twins agree to 2 years, $55M with Sonny Gray; White Sox land Dustin May (3 yrs, ~$52.5M)", "Gray to Twins (2y, $55M); May to White Sox (3y, ~$52.5M)", "https://www.espn.com/mlb/story/_/id/50328768/free-agency-tracker-offseason-trades-moves-2026-2027", "ESPN tracker"),
    it("Mariners get Maikel Garcia from Royals in a six-player trade; Astros are gauging interest in Christian Walker", "Mariners get M. Garcia (6-player deal); Astros shop C. Walker", "https://www.mlb.com/news/mlb-rumors-and-2026-27-free-agent-news-november-18", "ESPN / MLB.com")
   ]
  }
 },
 "memes": {
  "tagline": "Drew & Jess are watching the feeds so you don't have to",
  "intro": "What your kids might be saying at school this week, and one line on how to bring it up.",
  "memeOfTheWeek": "talk-doja",
  "levels": [
   {"level": "Elementary", "icon": "🎒", "items": [
    {"id": "roblox", "title": "Roblox: 'Steal An Egg' & 'Throw Food For Animals'",
     "what": "Steal An Egg is Roblox's #1 game (about 1.17M playing); Throw Food For Animals is #2 and up 58% on the week.",
     "means": "Pet-collecting games where other players can take your eggs; paid boosts are optional.",
     "tip": "Ask 'who's stealing your eggs?' Set chat to friends-only and a spending limit.",
     "links": [L("RBLXSTAT: Roblox weekly report Nov 9-15", "https://rblxstat.com/blog/roblox-weekly-report-2026-11-15"), L("SafeScreens: Roblox parent's guide", "https://safescreens.us/guides/gaming/roblox-experiences"), L("RoStats: Top Roblox games Nov 2026", "https://rostats.io/charts/2026-11")], "confirm": []},
    {"id": "six-seven", "title": "'6-7'",
     "what": "A catchphrase kids yell for laughs, often with a hands-weighing gesture.",
     "means": "No fixed meaning; some link it to LaMelo Ball (6'7\"). Already being mocked as overused.",
     "tip": "Laugh and ask them to show you the gesture; it's meant to confuse adults.",
     "links": [L("Reader's Digest: Gen Alpha slang", "https://www.rd.com/article/gen-alpha-slang/"), L("MadeForMums: parents' guide to slang", "https://www.madeformums.com/features/parents-guide-to-gen-alpha-slang/")], "confirm": []}
   ]},
   {"level": "Middle School", "icon": "📱", "items": [
    {"id": "talk-doja", "title": "'Talk To Me Doja' (Meme of the Week)",
     "what": "A TikTok dance trend copying a dance from the anime 'Yamada-kun and the Seven Witches' set to Doja Cat's 'Like That' (started Nov 7).",
     "means": "Kids film their own version next to the anime clip.",
     "tip": "Ask 'show me the dance?' Check the anime's rating before streaming it.",
     "links": [L("Know Your Meme: Talk To Me Doja", "https://knowyourmeme.com/editorials/guides/what-is-the-talk-to-me-doja-meme-the-viral-yamada-kun-and-the-seven-witches-memes-explained")],
     "confirm": ["Popularity is TikTok-side; X shows only ~38 posts in 7 days"]},
    {"id": "pennywide", "title": "'Pennywide' meme",
     "what": "A Halloween trick-or-treat video of a child in a Pennywise mask went viral and became memes mocking him.",
     "means": "A cruelty meme aimed at a real kid, remixed into brainrot edits.",
     "tip": "Ask 'would you laugh if that was your cousin?' It's a natural bridge to the bullying talk.",
     "links": [L("Know Your Meme: Pennywide", "https://trending.knowyourmeme.com/editorials/guides/what-is-the-pennywide-meme-the-viral-pennywise-house-video-and-memes-explained")], "confirm": []}
   ]},
   {"level": "High School", "icon": "🎓", "items": [
    {"id": "door-kick", "title": "The Door Kick Challenge",
     "what": "A TikTok trend: kick or pound a stranger's front door, film it, run.",
     "means": "Police say it can mean vandalism, trespass or burglary charges, and a scared homeowner may react.",
     "tip": "It's a crime, not a prank; Irvine PD says parents can be held accountable. Ask what they'd do if friends filmed it.",
     "links": [L("ABC7: Irvine police warning (Nov 12)", "https://abc7.com/story/irvine-police-warn-social-media-driven-door-kick-challenge-could-lead-criminal-charges/20033918/"), L("WBBH: Cape Coral incident (Nov 16)", "https://www.gulfcoastnewsnow.com/article/video-door-kick-challenge-cape-coral-florida/74444521"), L("KOBI: Talent, Oregon (Nov 12)", "https://kobi5.com/news/door-kicking-trend-is-growing-locally-five-incidents-reported-in-talent-319588/")],
     "confirm": ["No RGV incident found; X shows only ~39 posts in 7 days"]},
    {"id": "slang", "title": "Slang: aura, aura farming, cooked",
     "what": "'Aura' = someone's vibe; 'aura farming' = doing things to look cool online; 'cooked' = in trouble.",
     "means": "Words to question: 'huzz,' 'bop,' 'big back' can objectify or mock women and bodies.",
     "tip": "Be curious, not corrective: ask what a word means. Terms burn out fast.",
     "links": [L("MadeForMums: 45 Gen Alpha slang words", "https://www.madeformums.com/features/parents-guide-to-gen-alpha-slang/"), L("Reader's Digest: 24 Gen Alpha slang terms", "https://www.rd.com/article/gen-alpha-slang/"), L("Hello!: how to respond to bizarre slang", "https://www.hellomagazine.com/healthandbeauty/mother-and-baby/878329/your-gen-alpha-child-increasingly-bizarre-slang-how-to-respond/")], "confirm": []},
    {"id": "gta6", "title": "GTA 6 launch week",
     "what": "GTA VI was set to release Thu Nov 19 at midnight, rated M (17+). X volume jumped to ~255k posts on Nov 18.",
     "means": "Late nights and possible skipped school; some UK schools set attendance prizes.",
     "tip": "Is 17+ a rule or a suggestion at your house? (Jess has more on this in Block C.)",
     "links": [L("ABC News: parents and GTA 6", "https://abcnews.com/GMA/Family/parents-gta-6-kids/story?id=138089889"), L("Independent: UK schools and GTA 6", "https://www.independent.co.uk/tech/gta-6-release-schools-absentee-pupils-b3087400.html")], "confirm": ["Launch actually happened on time Nov 19"]}
   ]}
  ]
 }
}

PM = {
 "roblox": ("Roblox's #1 game: pet-collecting 'Steal An Egg' (1.17M playing); other players can grab your eggs.", "Ask 'who's stealing your eggs?' Friends-only chat, spending limit."),
 "six-seven": ("Catchphrase kids yell with a hands-weighing gesture; no fixed meaning, already called overused.", "Ask them to show you the gesture; it's meant to confuse adults."),
 "talk-doja": ("TikTok dance copying a scene from anime 'Yamada-kun and the Seven Witches' set to Doja Cat's 'Like That.'", "Ask 'show me the dance?' Check the anime's rating first."),
 "pennywide": ("Viral Halloween video of a kid in a Pennywise mask, turned into memes mocking him: cruelty aimed at a real kid.", "Ask 'would you laugh if that was your cousin?' Bridge to the bullying talk."),
 "door-kick": ("TikTok trend: pound on a stranger's door, film it, run. Police say vandalism, trespass or worse.", "A crime, not a prank; parents can be held accountable. What if friends filmed it?"),
 "slang": ("'Aura' = vibe; 'aura farming' = acting cool online; 'cooked' = in trouble. Question 'huzz,' 'bop,' 'big back.'", "Be curious: ask what a word means."),
 "gta6": ("GTA VI launches Thu Nov 19 at midnight, rated M (17+); ~255k X posts Nov 18. Late nights, skipped school.", "Is 17+ a rule or a suggestion at your house?"),
}
for lv in data["memes"]["levels"]:
    for it in lv["items"]:
        it["pwhat"], it["ptip"] = PM[it["id"]]
NOPRINT_RGV = ("Food Truck Park",)
for it in data["headlines"]["rgv"]:
    if any(k in it["title"] for k in NOPRINT_RGV): it["noprint"] = True
PT = {"mullin": "Mullin on outages and the LSU-Texas flight", "snl": "SNL: Mulaney, Bridgers, the 'Sister' sketch"}
PN = {
 "faa": ("Nov 13: FAA grounded all U.S. flights ~3:30-8:15 PM ET; legacy network swamped; FAA sees no cyberattack.", "Everybody wants it modernized; nobody wants it down for the upgrade.", "HRL, MFE, BRO issued advisories; Brownsville had 5 cancellations."),
 "mullin": ("DHS Sec. Mullin told House Homeland Security (Nov 18) the outages weren't a coordinated attack; defended flying to the LSU-Texas game.", "Fair question or cheap shot? The optics of flying to a game during a grounding.", "DHS runs the border: what are RGV ranchers, bridges and Border Patrol seeing?"),
 "snl": ("Nov 14: Mulaney hosted (7th time), Bridgers sang; 'CIA Meeting' cold open roasted tech CEOs.", "A cold open that skips politics and still lands; 'Sister' hit people in the gut.", "It roasted the same ground stop that put HRL, MFE, BRO on advisory."),
}
for n in data["nationalDesk"]:
    n["print"] = n["id"] in PN
    if n["id"] in PT: n["ptitle"] = PT[n["id"]]
    if n["id"] in PN: n["pfact"], n["pangle"], n["pvalley"] = PN[n["id"]]
json.dump(data, open(os.path.join(H, "packet-2026-11-23.json"), "w"), indent=2, ensure_ascii=False)
print("ok")
