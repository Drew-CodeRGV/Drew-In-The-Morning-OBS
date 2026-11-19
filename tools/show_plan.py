#!/usr/bin/env python3
"""Single source of truth for the Monday 60-minute plan.
Writes: ../run-of-show-monday.md  and  ../obs-data.json  (segments, segues, principles, callIns).
Run:  python3 tools/show_plan.py
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEN = 60
C = lambda i, p, s: {"id": i, "primary": p, "secondary": s}
L = lambda label, url: {"label": label, "url": url}
EMAIL_FLAG = "ditm@drewlentz.com (seen as the show inbox; CONFIRM BEFORE AIR that it is meant for public submissions)"

B = []
def blk(**k): B.append(k)

blk(id="A-cold-open", letter="A", title="Cold Open & Jingle", subject="Welcome, the hour's promise, listener tease",
    minutes=2, flex=False, color="#f2b705",
    headlines=["Good morning, Rio Grande Valley"],
    chyrons=[C("a1","Drew Lentz","Host · Drew in the Morning"), C("a2","Monday, Nov. 23, 2026","Live from McAllen, TX")],
    talking=["Jingle sting. \"Good morning, Rio Grande Valley. It's Monday, November 23.\"",
             "Promise the hour: local first (SpaceX vote, Pulido, school boards), then the National Desk, a Meme of the Week beat, and How We'd Talk to Our Kids with Jess.",
             "One-line listener tease: \"DM us or email, and we'll read it on air.\" No phone number exists, so don't announce one."],
    follow=[], transitions=["Let's start where the biggest local fight is: Starbase."], links=[], confirm=[])

blk(id="B-starbase-watch", letter="B", title="Starbase Watch: SpaceX, the Vote & the Launch", subject="Data center tax abatement, Flight 15, community impact",
    minutes=8, flex=True, trim_to=6, stretch_to=10, color="#e4572e",
    headlines=["Cameron County rejects SpaceX tax break hearing, 3-2","Starship ship caught by tower; booster aborts catch","FAA review: up to 456 launches a year; comments close Dec. 7","County passes Boca Chica Beach access resolution"],
    chyrons=[C("b1","Cameron County Vote","Abatement hearing denied 3-2 · Nov. 17"),C("b2","SpaceX Data Center","$24B · 10-yr, 100% abatement sought"),C("b3","State Air Permit","TCEQ issued Nov. 16 after Sept. pause"),C("b4","Starship Flight 15","Nov. 13 launch · ship caught Nov. 14"),C("b5","FAA Launch Review","Up to 456 launches a year · comments close Dec. 7"),C("b6","Boca Chica Beach","County resolution protects public access")],
    talking=["THE VOTE: Tue Nov 17, Cameron County commissioners voted 3-2 not to move toward a public hearing on SpaceX's request for a 10-year, 100% tax abatement on a $24B data center and gas power plant. Treviño and Lopez voted for the hearing (it would have been Dec 29). Lopez said \"it's dead in the water\" but stressed it was a vote about setting up public input, not approving the deal.",
             "SPACEX'S OWN WORDS: the application said that without the abatement it would \"redirect current and/or future investment to other super compute facility sites outside Cameron County.\" Residents and groups (South Texas Environmental Justice Network, Valley Interfaith, Surfrider) urged rejection.",
             "THE STATE SIDE: TCEQ issued the air permit Nov 16, after Gov. Abbott's September pause; environmental groups had alleged construction started without a permit. Gov.-elect Hinojosa has promised to freeze new data-center development and takes office in January.",
             "THE LAUNCH: Flight 15 lifted off Fri Nov 13. The ship reached orbit and was caught by the tower Nov 14; the booster aborted its catch and splashed down offshore. The nationwide FAA ground stop that day did not affect the flight (ValleyCentral).",
             "WHO FEELS IT: FAA review for up to 456 launches / 912 landings a year, comments close Dec 7. Residents describe debris, shaking windows and fishing worries; Playa Baghdad residents say they feel forgotten; Matamoros residents report cracks (allegation). Cameron County unanimously passed a Boca Chica Beach access resolution Nov 17; Starbase says \"nobody is buying or selling Boca Chica Beach.\"",
             "CONTEXT (depth): SpaceX also pledged $220M for Brownsville water projects (Daily McAllen Nov 14) and Brownsville secured another $30M SpaceX deposit (City of Brownsville Nov 17). Ask: is the deal \"jobs for infrastructure\" and who negotiates it?"],
    follow=["Does 'no tax break' mean 'no project'? What does the Valley get for being SpaceX's backyard, and who pays?",
            "If you were on that court, would you have voted for a hearing just to hear the public? (Lopez's framing)",
            "What would you ask SpaceX in writing before any abatement: water, power, jobs, beach access?",
            "Questions for officials: TCEQ (how was the permit issued while construction was alleged?), FAA (how is cumulative launch impact measured?), Starbase (what is the Dec hearing for?)."],
    transitions=["That's the headline. Now let's talk about who actually lives next to it.", "Hold that thought: I want to hear from people who aren't in the room where this got decided."],
    links=[L("MyRGV: commissioners reject SpaceX bid","https://myrgv.com/local-news/2026/11/17/cameron-county-commissioners-reject-spacex-bid-for-data-center-tax-break/"),L("KRGV: commissioners reject tax break","https://www.krgv.com/news/cameron-county-commissioners-reject-spacex-data-center-tax-break-request/"),L("Politico: Texas issues air permit","https://www.politico.com/news/2026/11/17/texas-issues-air-permit-for-massive-spacex-data-center-01170758"),L("Spaceflight Now: Flight 15","https://spaceflightnow.com/2026/11/13/live-coverage-starship-flight-15-attempts-to-recover-full-vehicle-in-double-launch-pad-catch/"),L("Daily McAllen: Starbase says nobody is buying Boca Chica Beach","https://dailymcallen.com/local-news/editions/11-14-2026"),L("KRGV: Boca Chica Beach resolution","https://www.krgv.com/news/cameron-county-commissioners-pass-resolution-to-protect-public-access-to-boca-chica-beach/")],
    confirm=["Dec 9 Starbase hearing date","Jobs figure (MyRGV 5,500 peak construction vs KRGV 500 new)","FAA public meeting date"])

blk(id="C-jess-gta6", letter="C", title="Jess Drop-In #1: GTA 6 Week & the Digital Generation", subject="GTA 6 launch, school attendance, sleep, screen time, AI in class",
    minutes=4, flex=False, jess=True, color="#8e6bbf",
    headlines=["GTA 6 launches Nov. 19 at midnight; rated M (17+)","UK schools use prizes and home visits to fight skipping","PSJA ISD sets student rules for AI use"],
    chyrons=[C("c1","Jess","Co-host · Drop-in Guest"),C("c2","GTA 6 Week","Sleep, school, screens · rated M (17+)"),C("c3","Texas Phone Rule","Phones off during the school day (HB 1481)"),C("c4","AI in the Classroom","PSJA guidebook: ask, cite, fact-check")],
    talking=["CHECK FIRST: did GTA 6 launch on time Thu Nov 19 (midnight, rated M/17+)? CONFIRM BEFORE AIR. X volume for \"GTA 6\" jumped to ~255k posts on Nov 18 (UTC day) from ~32-34k/day earlier that week (X counts, checked Nov 18).",
             "Context: UK schools used prize draws, minibus pickups and home visits to fight skipping; one school's letter said it's fine if your kid doesn't have the game. No RGV school warnings found. Texas: a fake Instagram post claimed Uvalde schools were closed; they weren't.",
             "Screen-time and sleep angle; phones off during the school day under Texas HB 1481. AI-in-school pointer: PSJA ISD's AI guidebook (Sept 2026) says get teacher permission, cite AI use, fact-check, never enter name/ID/address.",
             "Tease the signature segment: \"Later we're going to talk about the stuff other parents skip.\""],
    follow=["What did we say to our kids this week about it? Is 17+ a rule or a suggestion at your house?","Did anyone's kid stay up or stay home? Ask chat."],
    transitions=["Texas already bans phones during the school day. So what happens at 3:15 PM? Jess, that one's yours.","Thanks, Jess. Let's get back to the Valley."],
    links=[L("ABC News: parents and GTA 6","https://abcnews.com/GMA/Family/parents-gta-6-kids/story?id=138089889"),L("Independent: UK schools and GTA 6","https://www.independent.co.uk/tech/gta-6-release-schools-absentee-pupils-b3087400.html"),L("News4 San Antonio: fake Uvalde post","https://news4sanantonio.com/news/local/fake-instagram-account-claims-uvalde-schools-closed-for-gta-6-release"),L("TEA: HB 1481 phone rule","https://tea.texas.gov/taa-letters/implementation-texas-house-bill-1481-student-use-personal-communication-devices-school"),L("PSJA ISD AI guidebook","https://www.psjaisd.us/academics/psja-isd-ai-guidebook")],
    confirm=["GTA 6 actually launched on time Nov 19","Any RGV school/attendance reaction"])

blk(id="D-ballot-box", letter="D", title="Ballot Box Rewind: Pulido, Runoffs & the Valley Flip", subject="TX-15 result and Dec. 12 runoffs",
    minutes=6, flex=True, trim_to=4, stretch_to=8, color="#2a6f97",
    headlines=["Bobby Pulido defeats Rep. Monica De La Cruz in TX-15","Mission mayor, two council seats go to Dec. 12 runoffs","Weslaco commissioner-at-large runoff Dec. 12"],
    chyrons=[C("d1","TX-15: Bobby Pulido","Defeated De La Cruz · Takes office Jan. 3"),C("d2","TX-15 Result (unofficial)","Pulido 61.6% · De La Cruz 38.4%"),C("d3","Mission Mayor Runoff","Salinas vs. Gonzalez Garza · Dec. 12"),C("d4","Weslaco At-Large Runoff","Gonzalez Jr. vs. Salinas Jr. · Dec. 12")],
    talking=["PULIDO: Democrat Bobby Pulido (Tejano singer, Edinburg native) beat Rep. Monica De La Cruz in TX-15 on Nov 3. Ballotpedia (unofficial): 61.6% to 38.4%. He takes office Jan 3, 2027. Texas Tribune: calls himself a \"conservative Democrat,\" campaigned at concerts and quinceañeras.",
             "HISTORY / CONTEXT (depth): Trump carried the district by 18 points in 2024, and Republicans had redrawn Texas maps to gain Valley seats (Texas Tribune). So a double-digit Democratic win here is the Valley telling Austin and Washington something.",
             "NEXT UP, DEC 12 RUNOFFS: Mission mayor, Rick Salinas (34.81%) vs. Mayor Norie Gonzalez Garza (24.36%); Place 2 and Place 3 runoffs; Weslaco commissioner-at-large (Israel Gonzalez Jr. vs. Johnny J. Salinas Jr.). Early voting is reported Nov 30 to Dec 8.",
             "WHAT TO WATCH: certified totals; who endorses in the Mission runoff; turnout in a December runoff; what Pulido says about his first priorities before Jan 3."],
    follow=["What does a flipped district tell you about the Valley electorate?","What do local runoffs say about 'same old, same old' (Salinas's phrase)?","If you could ask Pulido one question before he's sworn in, what is it?","Questions for officials: Mission candidates on city manager stability, budget, drainage."],
    transitions=["We just watched an election come down to turnout. You know who doesn't get a ballot? The 10-year-old who's about to get a very big game this week.","One flipped district, one runoff, one tax break: put them together and what's the Valley telling Texas?"],
    links=[L("Texas Tribune: Pulido beats De La Cruz","https://www.texastribune.org/2026/11/03/texas-bobby-pulido-monica-de-la-cruz-congress-district-15-elections-2026/"),L("Ballotpedia: Bobby Pulido","https://ballotpedia.org/Bobby_Pulido"),L("MyRGV: Mission races to runoff","https://myrgv.com/local-news/2026/11/04/not-over-yet-nearly-all-mission-races-heading-to-runoff-elections/"),L("KRGV: Mission runoff Dec. 12","https://www.krgv.com/news/mission-mayoral-and-city-council-runoff-elections-set-for-dec-12/"),L("Hidalgo County runoff page","https://www.hidalgocounty.us/3526/December-12-2026-Local-Entities-Runoff-E")],
    confirm=["Certified vote totals","TX-34 result (not retrieved)","Early-voting dates"])

blk(id="E-city-hall-school-board", letter="E", title="City Hall & School Board Watch", subject="School boards, mayors and city managers",
    minutes=4, flex=True, trim_to=2, stretch_to=7, color="#2a9d8f",
    headlines=["Edinburg CISD adds new trustees; $3M stop-loss contract on agenda","PSJA ISD elects Griselda Quintanilla board president","Brownsville names Alan Guard permanent city manager"],
    chyrons=[C("e1","Edinburg CISD Board","New trustees from Nov. 3 election"),C("e2","PSJA ISD Board","3 new trustees sworn in · Nov. 16"),C("e3","McAllen City Commission","Fallek won District 5 special · May 2026"),C("e4","Brownsville City Manager","Alan Guard named permanent · June 2026")],
    talking=["SCHOOL BOARDS: Edinburg CISD, Gloria Alonzo unseated incumbent Minga Vela; Sandra Avila won the open seat; Flores and Garcia re-elected; board to approve a $3,072,278 stop-loss contract (CONFIRM it was seated/voted Nov 17). PSJA ISD swore in three trustees Nov 16 (Cabrera, Loredo, Chavez); Griselda Quintanilla is president. McAllen ISD: $4M insurance transfer for an $8.6M deficit (CONFIRM date). Brownsville ISD results not retrieved.",
             "CITY MANAGERS / MAYORS: McAllen, Michael Fallek won the District 5 special in May; Isaac Tawil city manager since Sept 2024. Brownsville named Alan Guard permanent city manager (June 2026); San Benito named an interim manager (June 2026). CONFIRM dates for Pharr (Andy Harvey resignation) and Mission (Mike Perez on leave) before airing.",
             "OPINION (flag as opinion): why do so many Valley cities have a revolving door at the top, and what does it cost residents?"],
    follow=["What would you ask a brand-new trustee in their first month?","What do you actually know about your district's budget deficit?","Questions for officials: why a $3M stop-loss contract, and what changed in claims costs?"],
    transitions=["Two school boards' worth of decisions land on our kids. Here's what we'd want trustees to ask about screens and AI in class.","Every campaign promise has a kid somewhere in it."],
    links=[L("Edinburg Advocate: Edinburg CISD seats new members","https://theedinburgadvocate.com/2026/11/edinburg-cisd-board-to-seat-new-members-approve-3-million-stop-loss-insurance-contract-at-special-meeting-tuesday-nov-17/"),L("PSJA ISD: swears in trustees","https://www.psjaisd.us/school-news-details/~board/pharr-san-juan-alamo-isd-news/post/psja-isd-swears-in-three-trustees-elects-new-board-leadership"),L("ValleyCentral: Fallek wins District 5","https://www.valleycentral.com/valleycentrals-local-elections-hq/michael-fallek-officially-declared-winner-in-district-5-city-commission-race/"),L("MyRGV: Brownsville names Alan Guard","https://myrgv.com/featured/2026/06/17/brownsville-appoints-interim-city-manager-alan-guard-to-permanent-position/")],
    confirm=["Edinburg CISD seating/vote happened Nov 17","McAllen ISD board vote date","Pharr city manager resignation date","Mission city manager leave"])

blk(id="F-zoho-park", letter="F", title="Zoho & the Park", subject="McAllen disc golf park rezoning and Zoho's Valley footprint",
    minutes=3, flex=True, trim_to=0, stretch_to=5, color="#bc6c25",
    headlines=["2023: McAllen rezoned disc golf park for Zoho","Zoho bought Edinburg's Echo Hotel property in 2025"],
    chyrons=[C("f1","Zoho & the Disc Golf Park","Rezoned July 2023 · commission vote 6-0"),C("f2","Zoho in the Valley","Edinburg Echo Hotel property bought Apr. 2025")],
    talking=["VERIFIED BACKGROUND: July 24, 2023, McAllen's commission voted unanimously (all six present) to rezone the ~90-acre disc golf park (\"Green Jay Park\") for Zoho after P&Z voted no and residents gave ~3 hours of comment. Zoho: ~8-10 acres, ~$10M, up to 500 jobs, no tax incentives sought; the sale still needed approval and FEMA conditions. Zoho bought the Echo Hotel property in Edinburg (April 2025).",
             "CONFIRM BEFORE AIR: the claim that the city donated park land to Zoho. No source for a donation or a 2026 update was found. Bring the source and date, or reframe as \"what happened to the park?\" and ask chat. Do not say \"donated.\""],
    follow=["How much public land should a city trade for jobs, and who decides?","Where does this stand today? Does anyone in chat know?"],
    transitions=["Forget the press release for a second: what does this change for somebody's Tuesday?"],
    links=[L("MyRGV 2023: commission rezones park","https://myrgv.com/local-news/2023/07/25/despite-protest-mcallen-commission-rezones-park-for-austin-tech-company/"),L("KRGV 2023: commissioners vote to rezone","https://www.krgv.com/news/city-of-mcallen-commissioners-vote-to-rezone-disc-golf-course/"),L("Texas Border Business: Echo Hotel","https://texasborderbusiness.com/major-investment-in-echo-hotel-property-coming-to-edinburg/")],
    confirm=["Park DONATION to Zoho: no source found","Any 2026 update"])

blk(id="G-metro-desk", letter="G", title="McAllen Metro Desk: Economic Development", subject="Jobs, projects and city news",
    minutes=3, flex=True, trim_to=2, stretch_to=4, color="#43aa8b",
    headlines=["McAllen EDC wins state award for Valeo's $225M plant","Food Truck Park closure delayed to Jan. 14, 2027","Texas A&M McAllen to build $50M health building"],
    chyrons=[C("g1","McAllen EDC","State award · Valeo $225M plant"),C("g2","Food Truck Park","Closure moved from Dec. 14 to Jan. 14"),C("g3","Texas A&M McAllen","$50M health building · starts Dec. 2026"),C("g4","US 281 Edinburg","One NB lane through May 2027")],
    talking=["McAllen EDC won the 2026 Texas EDC award for Valeo's $225M plant (500+ direct jobs projected); a new Amazon last-mile station opened.",
             "Food Truck Park closure moved to Jan 14, 2027; the Chamber waives rent; a vendor: \"all of our savings are going into it.\"",
             "Texas A&M McAllen: $50M health building; 650+ students (+30%); construction to start Dec 2026.",
             "Quick hits: US 281 Edinburg one northbound lane through May 2027; Holiday Parade promo (parade date CONFIRM). USDA confirmed another screwworm case in Starr County cattle; a USDA job fair for 228 jobs at the Edinburg sterile-fly facility ran through Nov 19."],
    follow=["Great, we're growing. Can a kid who grows up here afford to stay?"],
    transitions=["A $225 million plant means 500 jobs on paper. Let's talk about what a good job does for a family dinner table.","A new health building means local kids can study nursing without leaving home. That's the version of growth I like."],
    links=[L("Daily McAllen Nov 16","https://dailymcallen.com/local-news/editions/11-16-2026"),L("Daily McAllen Nov 17","https://dailymcallen.com/local-news/editions/11-17-2026"),L("Daily McAllen Nov 18","https://dailymcallen.com/local-news/editions/11-18-2026"),L("The RGV News: Nov 17 brief","https://thergvnews.com/reviews/day/2026-11-17")],
    confirm=["McAllen Holiday Parade date"])

blk(id="H-open-format", letter="H", title="Wait, Don't Tell Me: Trending + Open Story", subject="Trending slot: viral, celebrity, culture and sports stories a well-informed host should know (pick 1 to 3 with a Valley riff), or an open local wildcard: Power & Pipes, Overheard in the Valley, Politiquera",
    minutes=3, flex=True, trim_to=0, stretch_to=6, color="#577590",
    headlines=["Hidalgo County can't block data centers outside city limits","Speer Library bus stop march and petition"],
    chyrons=[C("h0","Wait, Don't Tell Me","What everybody's talking about · pick 1 to 3"),C("h1","Judge Richard Cortez","Hidalgo County Judge · Citizens League"),C("h2","Texas Power Grid","~98 GW now · ~100 GW more by 2027"),C("h3","Overheard in the Valley","From r/RioGrandeValley"),C("h4","Politiquera Corner","politiquera.com"),C("h5","Drew Lentz","Wireless Engineer · The Wireless Nerd")],
    talking=["TRENDING (\"WAIT, DON'T TELL ME\"): open the studio page section \"Trending: Wait, Don't Tell Me\" (6 to 10 items, each with a one-line summary, a suggested riff and a source link; the print packet carries the top 5). Pick 1 to 3: the best riff with a Valley tie, not the most famous story. Format: Drew reacts first (\"wait, don't tell me...\"), Jess adds the angle, one link on screen. Items marked CONFIRM BEFORE AIR are thinly sourced: verify or skip. Never duplicate a National Desk story. THIS WEEK'S SAMPLE BANK: CMA Awards (Ella Langley, \"Choosin' Texas\"), Musk \"I'm not MAGA\" (Starbase tie), the viral Mexican quince stadium party (Valley quince tie), Giannis vs. the Bucks, Pattinson as Bond.",
             "MENU (OPEN LOCAL WILDCARD). POWER & PIPES: Hidalgo County Judge Richard Cortez says the county can't unilaterally block data centers in unincorporated areas but can negotiate; Texas grid ~98 GW with ~100 GW more slated by end of 2027. Drew's wheelhouse: satellites eyeing space compute (Broadband Breakfast Nov 18) and the AT&T/AST SpaceMobile handoff test.",
             "OVERHEARD IN THE VALLEY: backup verified item, Speer Memorial Library Route 20 bus-stop march/petition (Nov 14; stop reportedly unserviced since ~2017). PREP: pull 2-3 top posts Sunday night from r/RioGrandeValley, r/RGVEvents, r/McAllen (Top, Past Week).",
             "POLITIQUERA CORNER: politiquera.com campaign data; pre-pick one chart from /2026midterms (Mission's Dec 12 runoff is a natural tie-in). No data was pulled for this sample.",
             "WILDCARD: whatever broke this morning. Check KRGV, MyRGV, ValleyCentral first."],
    follow=["Wait, don't tell me: what's the one story you saw this morning that you want us to explain?","If you could attach one condition to a data center in the Valley (jobs, water, power or internet), which?"],
    transitions=["Okay, that's what the internet is losing its mind over this morning. Now the big national stories, and why they land in the Valley.","Both sides said they're for the Valley. Let's find out what 'for the Valley' costs and who's paying."],
    links=[L("Daily McAllen Nov 17 (Cortez on data centers)","https://dailymcallen.com/local-news/editions/11-17-2026"),L("r/RioGrandeValley: Speer Library march","https://www.reddit.com/r/RioGrandeValley/comments/1xjnz54/community_march_to_petition_for_the_speer/"),L("Politiquera","https://politiquera.com/")],
    confirm=["Pull live Reddit top-of-week titles","Choose the Politiquera data point"])

blk(id="I-national-desk", letter="I", title="The National Desk", subject="Big national stories of the week, with a Valley angle (fact, then opinion, then 'why it matters here')",
    minutes=6, flex=True, trim_to=4, stretch_to=8, color="#6d597a",
    headlines=["FAA ground stop: legacy network, a router and a long weekend","DHS Sec. Mullin testifies on outages, LSU-Texas flight","SNL: Mulaney's CIA cold open and the 'Sister' sketch","Nvidia's Jensen Huang resigns; SNL spoofs it","Texas Ten Commandments law faces an uncertain future"],
    chyrons=[C("i1","National Desk","The big stories · and why they matter here"),C("i2","FAA Nationwide Ground Stop","Nov. 13 · legacy network overwhelmed by data"),C("i3","Valley Airports","HRL, MFE, BRO issued travel advisories"),C("i4","DHS Sec. Markwayne Mullin","House Homeland Security hearing · Nov. 18"),C("i5","SNL: John Mulaney Hosts","Phoebe Bridgers · Nov. 14 · 7th time hosting"),C("i6","SNL: The 'Sister' Sketch","Pretaped elder-care ad · 5.8M YouTube views")],
    talking=["Keep it conversational: one-line fact, your take (fair, a little spicy), then 'why it matters in the Valley.' Pick 3 of the 5. Local stays the star.",
             "1) FAA GROUND STOP (Fri Nov 13). FACT: ~3:30 p.m. ET the FAA issued a nationwide ground stop; flights resumed ~8:15 p.m. ET. FAA: legacy equipment became unstable when data flooded its FTI network; two suspected sites, a radar site in Amarillo, TX and a radio site in El Dorado, AR where L3Harris was deploying a new router; 17 of 22 en route centers affected; ~3,500 aircraft landed safely; about 12,462 flights canceled that day (FAA). No indication of a cyberattack (FAA). It was the second nationwide ground stop since 9/11 (ABC, ValleyCentral). Wed Nov 18: FAA Administrator Bryan Bedford told Congress \"blame me\" (ABC). ANGLE: everybody wants the airline system modernized and nobody wants it down for the upgrade; the fix broke it on install number 69, per Sec. Duffy. VALLEY TIE: Harlingen's Valley International said incoming banks from Houston, DFW and Austin couldn't depart; McAllen, Brownsville and HRL issued advisories; Brownsville still showed 5 cancellations and 2 delays at 10 p.m. (KRGV, ValleyCentral). Starship Flight 15 was not affected.",
             "2) THE MULLIN TESTIMONY (Wed Nov 18). FACT: DHS Secretary Markwayne Mullin testified before the House Homeland Security Committee at \"Worldwide Threats to the Homeland: 25 Years After 9/11,\" with DNI Jay Clayton and FBI Deputy Director Christopher Raia. Clayton: the recent outages are \"separate service outages associated with maintenance and technical changes,\" not a coordinated or state-sponsored attack. Mullin defended taking a government plane to the LSU-Texas game right after the ground stop (said he wanted to be a good uncle; will reimburse the government) and was pressed on ICE training. ANGLE: fair question or cheap shot? Either way, the optics of flying to a football game during a grounding are rough. VALLEY TIE: DHS runs the border; his written testimony touts Southwest border apprehensions down 58% in FY2026, which is DHS's claim; ask what Valley ranchers, bridges and Border Patrol sectors are seeing. CONFIRM BEFORE AIR: Drew said \"Mullen\"; this is Sec. Markwayne Mullin (spelled with an i), the only Mullin/Mullen testimony found this week.",
             "3) SNL (Sat Nov 14, S52E06). FACT: John Mulaney hosted for the 7th time; Phoebe Bridgers was musical guest (\"Bobby,\" \"Still Standing\"). Cold open: \"CIA Meeting,\" Mulaney as a CIA officer lecturing Musk, Altman, Thiel, Zuckerberg and Amodei about honey-trap spies after the Jensen Huang scandal, with Bowen Yang returning as Huang; it also jabbed the ground stop and the Outlook outage. Other sketches: \"Sister,\" \"Plane Crash,\" \"Gettin' It Done,\" \"Woodstock,\" \"Kathy,\" and a Central Park carriage ride musical sketch. DID IT LAND: EW: \"easily the best episode of this season\"; Boston.com: \"far and away the best of Season 52\"; ratings 4.45M, down 20% from the prior week (Showbiz411). THE 'SISTER' VIDEO: a pretaped fake elder-care testimonial ad (Jane Wickline as the sister), on SNL's YouTube channel (published Nov 14, 2:59, ~5.8M views when checked Nov 18). CONFIRM BEFORE AIR that 'Sister' is the sister video Drew meant. Last new episode before Thanksgiving; the next is in December (Amanda Seyfried, per EW). ANGLE: it's the rare cold open that skips politics and still lands. VALLEY TIE: the cold open roasted the same ground stop that led HRL, MFE and BRO to issue travel advisories; 'Sister' is a caregiving story, so ask chat who is the 'Sister' in their family.",
             "4) NVIDIA'S JENSEN HUANG RESIGNS (Nov 12). FACT: Nvidia announced Huang resigned as president, CEO and board member effective immediately; CFO Colette Kress is interim CEO; Harvey C. Jones is the first board chair (Nvidia press release). Mainstream reports link it to an alleged affair with a suspected Chinese spy (SNL's cold open built on it); verify the allegations through a reported source before characterizing them. ANGLE: the AI boom's biggest face is gone, and it's still building the chips for every data center on earth. VALLEY TIE: Starbase's $24B data center is exactly that kind of AI compute fight. CONFIRM BEFORE AIR on any allegation detail.",
             "5) TEXAS TEN COMMANDMENTS (ABC, Nov 18). FACT: ABC reports the Democratic midterm sweep has put Texas's classroom Ten Commandments mandate in doubt; the law remains in effect and legal battles are headed to the Supreme Court. ANGLE: whatever you think of it, parents deserve a clear answer about what's on the classroom wall. VALLEY TIE: it applies in every RGV school; ask what your child's classroom has up. CONFIRM BEFORE AIR on details of repeal efforts."],
    follow=["Would you board a flight tomorrow? Be honest.","Should a Cabinet secretary skip the football game after a national outage? Ask chat.","Did SNL's 'Sister' hit you in the gut or are we overthinking it?","'Current FAA flight cuts': none found in the sources checked this week. CONFIRM BEFORE AIR if Drew meant something else."],
    transitions=["Okay, that's the 30,000-foot view. Now, what does it mean at 1,000 feet over the Valley?","This looks like a McAllen story. It's really a story about every border town trying to grow without losing itself.","Zoom out: whatever is happening in the world, Valley travelers feel it at MFE, HRL and BRO."],
    links=[L("FAA: Nationwide Ground Stop Q&A","https://www.faa.gov/newsroom/nationwide-ground-stop-questions-and-answers"),L("ABC: Mullin grilled, FAA head says 'blame me'","https://abcnews.com/Politics/mullin-faces-congressional-hearing-wake-historic-nationwide-ground/story?id=138226960"),L("House Homeland Security: Mullin written testimony (PDF)","https://homeland.house.gov/wp-content/uploads/2026/11/2026-11-18-HRG-Testimony-Mullin.pdf"),L("ValleyCentral: Valley airports issue advisories","https://www.valleycentral.com/news/local-news/valley-airports-airports-issue-travel-advisories-amid-faa-nationwide-ground-stop/amp/"),L("KRGV: Brownsville airport after ground stop","https://www.krgv.com/news/cancellations-and-delays-linger-at-brownsville-airport-after-nationwide-faa-ground-stop-ends/"),L("YouTube: SNL 'Sister'","https://www.youtube.com/watch?v=-X9dxL17t1k"),L("YouTube: SNL 'CIA Meeting' cold open","https://www.youtube.com/watch?v=R_8UPhJNrZ4"),L("EW: SNL recap","https://ew.com/snl-recap-john-mulaney-hosts-seventh-time-phoebe-bridgers-musical-guest-12253185"),L("Boston.com: SNL recap","https://www.boston.com/culture/entertainment/2026/11/15/snl-recap-john-mulaney-2026/"),L("Showbiz411: SNL ratings","https://www.showbiz411.com/2026/11/18/john-mulaney-phoebe-bridgers-snl-best-this-season-drops-back-to-season-average-ratings-down-20-from-last-weeks-high"),L("Nvidia press release: CEO transition","https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-CEO-Transition/default.aspx"),L("ABC: Ten Commandments in Texas classrooms","https://abcnews.com/Politics/democratic-wave-upends-battle-ten-commandments-texas-classrooms/story?id=138118010")],
    confirm=["'Mullen' = Sec. Markwayne Mullin (confirm with Drew)","'Sister video' = SNL 'Sister' sketch (confirm with Drew)","Any allegation details on Jensen Huang","Any current FAA flight cuts (none found)","Refresh everything Sunday night"])

blk(id="J-listener-line-1", letter="J", title="Listener Line #1: Your Topics & DMs", subject="Read-outs of topic submissions and comments",
    minutes=2, flex=False, color="#f4a261",
    headlines=["Send us your topics: DM or email"],
    chyrons=[C("j1","Send Us Your Topics","DM @drewinthemorning or email the show"),C("j2","Got a Question?","Comment in chat, DM, or email · anonymous is fine"),C("j3","Next Monday: Your Questions","Comment, DM or email by Sunday night")],
    talking=["Read 1-2 submissions (first names only; nothing from DMs or email without the sender's OK).",
             "How to reach us: DMs on @drewinthemorning (Instagram, TikTok), YouTube comments, the Facebook page, and email at ditm@drewlentz.com (CONFIRM BEFORE AIR: the address was seen as the show inbox; confirm it is for public use).",
             "No call-in phone number exists, so don't announce one. A Restream guest link is UNVERIFIED (Drew to generate one) before inviting live call-ins."],
    follow=["What's the one thing happening in your neighborhood that nobody is covering?"],
    transitions=["Let's see how the next generation is talking. Time for the Meme of the Week."],
    links=[L("Call-ins: how submissions work (call-ins.md)","call-ins.md")],
    confirm=[EMAIL_FLAG, "Restream guest link (unverified)"])

blk(id="K-meme-of-the-week", letter="K", title="Meme of the Week: What the Kids Are Talking About", subject="Trending internet culture for parents: Elementary, Middle School, High School",
    minutes=3, flex=True, trim_to=2, stretch_to=4, color="#ff7f50",
    headlines=["Drew & Jess are watching the feeds so you don't have to"],
    chyrons=[C("k1","Meme of the Week","What your kids might be saying at school"),C("k2","Drew & Jess Are Watching","The feeds so you don't have to"),C("k3","Elementary · Middle · High","Three levels of kid culture")],
    talking=["Use the packet's Meme of the Week card (one fun beat, 3 minutes): explain the meme, what it means, and one \"how to bring it up\" tip. Items are sourced in the packet (Know Your Meme, RBLXSTAT/SafeScreens, Reader's Digest, local police warnings).",
             "Always include one 'what parents should know' line, e.g. the Door Kick Challenge is a crime, not a prank (Irvine PD, Nov 12).",
             "Mark anything thin as CONFIRM BEFORE AIR (X volume for several trends is low, so popularity is TikTok-side and unverified)."],
    follow=["Ask chat: what's the weirdest thing your kid said this week?"],
    transitions=["That's the fun stuff. Now the part other parents skip."],
    links=[L("Know Your Meme: Talk To Me Doja","https://knowyourmeme.com/editorials/guides/what-is-the-talk-to-me-doja-meme-the-viral-yamada-kun-and-the-seven-witches-memes-explained"),L("ABC7: Irvine PD on door kick challenge","https://abc7.com/story/irvine-police-warn-social-media-driven-door-kick-challenge-could-lead-criminal-charges/20033918/")],
    confirm=["Meme popularity measured on TikTok; X volume is low"])

blk(id="L-how-wed-talk-to-our-kids", letter="L", title="How We'd Talk to Our Kids", subject="Open, honest parenting talk for parents of a 10- and 14-year-old, with Jess",
    minutes=12, flex=True, trim_to=10, stretch_to=15, signature=True, recurring=True, jess=True, color="#e76f51",
    headlines=["How We'd Talk to Our Kids: no judgment, just how we'd say it","Strangers in the game chat: grooming and sextortion","When a kid is hurting: warning signs and 988"],
    chyrons=[C("l1","How We'd Talk to Our Kids","Open · Honest · No judgment"),C("l2","Ages 10 and 14","What we'd say to each"),C("l3","Jess","Co-host · How We'd Talk to Our Kids"),C("l4","Strangers in the Game Chat","Grooming and sextortion · know the signs"),C("l5","You Will Never Be in Trouble","The sentence kids need to hear"),C("l6","When a Kid Is Hurting","Warning signs · talk early"),C("l7","Call or Text 988","Suicide & Crisis Lifeline · 24/7 · 988lifeline.org"),C("l8","Send Us Your Hard Question","Email or DM · anonymous on air"),C("l9","Listener Story","Shared with permission · first name only")],
    talking=["Signature, recurring segment. Never skipped; it stretches to ~15 min if flex blocks are trimmed. Aimed at parents of a 10-year-old and a 14-year-old. Open, frank, practical, not preachy. Drew and Jess talk like parents, not experts: \"here's what we'd say.\" OPEN WITH: \"No judgment here. If you've been avoiding this conversation, today's the easy day to start.\"",
             "TOPIC 1 (~5 min): Strangers in the game chat, grooming & sextortion. WHY NOW: a huge new game just launched and kids are online late. FBI: offenders get an explicit image, then demand money or gift cards; paying doesn't stop it; they often pose as someone else and move the chat to another app. TO THE 10-YEAR-OLD: \"People online can pretend to be anyone. If anyone asks for a picture of you, or says keep this secret, that's a red flag, even if they're nice. Come tell me. You will never be in trouble for telling me.\" TO THE 14-YEAR-OLD: \"Here's exactly how this works: someone friendly, a photo request, then threats and a demand for gift cards. It's a crime done by pros, and it happens to smart kids. If it happens, stop replying, don't pay, screenshot everything, and tell us right away. My first move is to help.\" PARENT PRACTICALS: phones out of bedrooms overnight; know which games have voice/text chat; watch for gift-card requests, secrecy, phone in the bathroom late; if it happens: save everything, don't forward images from the child's device, report to law enforcement/NCMEC; Take It Down (takeitdown.ncmec.org) can help remove images of someone under 18.",
             "LISTENER STORY MOMENT (~1-2 min): invite a listener story or question from DMs/email (first name only, with permission; CONFIRM the sender agreed to be read on air). No live caller unless a Restream guest link exists.",
             "TOPIC 2 (~5 min): When a kid is hurting: group-chat cruelty, self-harm warning signs, suicide (988). WHY NOW: Suicide Prevention Month (Sept) and Bullying Prevention Month (Oct) just ended; the problem doesn't end with the calendar. FBI links sextortion to suicides; NIMH and AAP list warning signs. TO THE 10-YEAR-OLD: \"If a group chat gets mean, or someone is being left out, you can screenshot it and show me. Telling isn't snitching. And if you ever feel really sad or like you can't stop feeling bad, tell me. Nothing is too big or too weird.\" TO THE 14-YEAR-OLD: \"Do you know anyone who's been talking about not wanting to be here, or hurting themselves? You can tell me about a friend. And if it's ever you, I'd rather have the hard conversation than not have you. Call or text 988 any time, even if you can't talk to me yet.\" WARNING SIGNS (NIMH/AAP/NSPCC): talking about wanting to die or being a burden, hopelessness, withdrawing, giving things away, big mood or sleep changes, long sleeves in hot weather, unexplained cuts, more drug/alcohol use. ON AIR, SAY: \"If you or your child is in crisis, call or text 988, or chat at 988lifeline.org. If someone is in immediate danger, call 911.\"",
             "TONE: don't lecture; admit it's hard. AAP suggestion: \"This is hard for me to even think about because I care about you.\"",
             "FUTURE TOPICS (pool): early porn exposure (AAP: ~15% first see it under 11) · sharing nudes and deepfakes (Take It Down Act; Texas HB 149) · vaping · AI companions (Common Sense: 72% of teens have used them) · puberty and body image · group-chat cruelty · screen time/obsessive computer use · AI in the curriculum. Verify any statistic before quoting it (e.g., CDC 13.8% electronic bullying).",
             "CLOSE: \"Send us the question you're afraid to ask: email or DM, you stay anonymous on air.\""],
    follow=["Jess: What was the first time you remember us having this talk, and how did it go? (your story here)","What's one sentence you wish your parents had said to you?","If your 14-year-old rolled their eyes, what would you try next?","If your child told you something scary tomorrow, what would your first sentence be?"],
    transitions=["Okay, time for the part of the show other parents skip. No judgment, just how we'd say it.","If one of those conversations feels huge, start with one sentence. Now, back to the Valley.","If you need to step away after that, there's no shame in it. 988, any time. Let's reset with something local."],
    links=[L("FBI: sextortion","https://www.fbi.gov/how-we-can-help-you/scams-and-safety/common-frauds-and-scams/sextortion"),L("DHS: Know2Protect sextortion PDF","https://www.dhs.gov/sites/default/files/2026-08/26_0806_k2p_p2p-t2p-sextortion.pdf"),L("NCMEC: Take It Down","https://takeitdown.ncmec.org/"),L("NIMH: warning signs of suicide","https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide"),L("AAP HealthyChildren: when children and teens self-harm","https://www.healthychildren.org/English/health-issues/conditions/emotional-problems/Pages/when-children-and-teens-self-harm.aspx")],
    confirm=["Verify any statistic before quoting it","Listener-story permission"])

blk(id="M-listener-line-2-wrap", letter="M", title="Listener Line #2, Look Ahead & Wrap (Jess back in)", subject="Calendar, topic requests, socials, sign-off",
    minutes=4, flex=False, jess=True, color="#264653",
    headlines=["See you next Monday at 8 AM"],
    chyrons=[C("m1","Jess","Co-host · Drop-in Guest"),C("m2","Coming Up","Thanksgiving · Thu., Nov. 26"),C("m3","Runoff Day","Mission and Weslaco · Dec. 12"),C("m4","FAA Comments Close","Starship expansion · Dec. 7"),C("m5","Follow @drewinthemorning","IG · TikTok · YouTube · Facebook"),C("m6","Next Monday, 8:00 AM CT","Drew in the Morning · Nov. 30")],
    talking=["Look ahead: Thanksgiving Thu Nov 26 · FAA comments close Dec 7 · Edinburg Night of Lights Parade Dec 4 · Mission/Weslaco runoffs Dec 12 (early voting from Nov 30) · Food Truck Park closes Jan 14, 2027 · Cameron abatement hearing would have been Dec 29 (now off).",
             "Listener line #2: ask for next week's topics. DMs and ditm@drewlentz.com (CONFIRM BEFORE AIR). No phone number.",
             "Jess back in: one thing she's watching this week; favorite moment. Socials: IG/TikTok @drewinthemorning · YouTube @DrewintheMorning · Facebook page. Tease Mon Nov 30, 8 AM CT. Jingle out."],
    follow=[], transitions=[], links=[L("Show social calendar (draft)","social-calendar.md")],
    confirm=["Early-voting dates", EMAIL_FLAG])

# ---- RESTRUCTURE (Nov 18, 5th update): flowing 12-block open-format menu A-L.
# The legacy blocks above (A-M) are the raw material; the blocks below re-compose them. Nothing here is invented:
# every talking point, chyron and link comes from the legacy blocks, the packet data, or is a process note.
OLD = {b["letter"]: b for b in B}
def lk(*letters, only=None):
    out, seen = [], set()
    for lt in letters:
        for l in OLD[lt]["links"]:
            if only and not any(k.lower() in l["label"].lower() for k in only): continue
            if l["url"] in seen: continue
            seen.add(l["url"]); out.append(l)
    return out
def cy(letter, items):
    return [C(f"{letter.lower()}{i}", p, s) for i, (p, s) in enumerate(items, 1)]
def oc(letter, ids):  # reuse legacy chyrons by id, re-id them
    pool = {c["id"]: c for b in B for c in b["chyrons"]}
    return [C(f"{letter.lower()}{i}", pool[x]["primary"], pool[x]["secondary"]) for i, x in enumerate(ids, 1)]

PACKET_DATA = os.path.join(ROOT, "packet", "data", "packet-2026-11-23.json")
_pk = json.load(open(PACKET_DATA)) if os.path.exists(PACKET_DATA) else {}
_texas = _pk.get("headlines", {}).get("texas", [])

NB = []
def nb(**k): NB.append(k)

nb(id="A-cold-open", letter="A", title="Cold Open & Jingle", short="Cold Open", subject="Jingle, the filled-in cold open, the hour's promise",
   minutes=2, flex=False, color="#f2b705",
   headlines=["Good morning, Rio Grande Valley"],
   chyrons=oc("A", ["a1", "a2"]),
   talking=["JINGLE: \"Drew in the Morning. Your Valley, your news, your morning.\" (alternates in cold-open.md)",
            "COLD OPEN: read the paragraph the packet builds each morning (card at the top of the studio page; also in the PDF, txt and email, and in obs-data.json under coldOpen). It is one flowing paragraph, about 45 seconds, filled with today's real headlines.",
            "Listener tease at the end of the open: DMs or ditm@drewlentz.com (CONFIRM BEFORE AIR). No phone number exists, so don't announce one."],
   follow=[], transitions=["Quick check-in on what I've been up to this week, then we jump into the Valley."], links=[L("Cold open template and jingle (cold-open.md)", "cold-open.md")],
   confirm=["Unconfirmed teased items are listed under the cold open on the studio page"])

nb(id="B-up-to", letter="B", title="What I've Been Up To This Week", short="Up To", subject="Personal touchpoint (2-3 min): public-facing things Drew and Jess did this week, then straight into Local news",
   minutes=3, flex=True, trim_to=2, stretch_to=4, jess=False, color="#d1495b",
   headlines=["What I've been up to this week"],
   chyrons=cy("B", [("What I've Been Up To", "This week · Drew & Jess"), ("This Week", "Talks, conferences & community events")]),
   talking=["SCRIPT: read the paragraph the packet builds (field up_to_script; it appears on the studio page, PDF, txt, email and in obs-data.json under upTo). 2 to 3 minutes, conversational, then drop into Local news.",
            "EVENTS: the list under the script (field up_to[]: date, title, type conference/presentation/meeting/appearance, who Drew/Jess, optional public link). Every item is CONFIRM BEFORE AIR: eyeball each one and cut anything you don't want said on air.",
            "NO EVENTS: if nothing is found the script says so plainly (\"Quiet week on the calendar...\") and the packet notes \"No calendar events found\". Do not make something up.",
            "PRIVACY (read on air): only public-facing participation: talks, conferences, panels, appearances, community events. Never personal, medical, financial, legal, client-confidential or private 1:1 meetings, and never name private individuals."],
   follow=["Jess: anything from your week worth a mention (a school event, a community thing)? Ask live; nothing here is pre-filled for her."],
   transitions=["Okay, enough about me. Let's get into the Valley.", "That's my week. Here's what the Valley's been up to."],
   links=[], confirm=["Every up_to item: CONFIRM BEFORE AIR (Drew eyeballs the list)", "Calendar is not connected, so events come from email only"])

_c = OLD["B"]; _hw = OLD["H"]
nb(id="C-local-news", letter="C", title="Local News", short="Local News", subject="Top Valley stories: the Starbase/SpaceX vote and launch, Overheard in the Valley, whatever broke this morning",
   minutes=8, flex=True, trim_to=6, stretch_to=10, color="#e4572e",
   headlines=_c["headlines"],
   chyrons=oc("C", ["b1", "b2", "b3", "b4", "b5", "b6"]),
   talking=_c["talking"] + [_hw["talking"][2], _hw["talking"][4]],
   follow=_c["follow"],
   transitions=["That's the headline. Now let's talk about who actually lives next to it.", "Hold that thought: that vote is local politics. Let's go there."],
   links=_c["links"] + [l for l in _hw["links"] if "r/RioGrandeValley" in l["label"]],
   confirm=_c["confirm"] + ["Pull live Reddit top-of-week titles (r/RioGrandeValley, r/RGVEvents, r/McAllen)"])

_d = OLD["D"]
nb(id="D-local-politics", letter="D", title="Local Politics", short="Local Politics", subject="Races, candidates and runoffs: TX-15 (Pulido), the Dec. 12 Mission and Weslaco runoffs",
   minutes=6, flex=True, trim_to=4, stretch_to=8, color="#2a6f97",
   headlines=_d["headlines"], chyrons=oc("D", ["d1", "d2", "d3", "d4"]),
   talking=_d["talking"] + ["POLITIQUERA CORNER (optional): politiquera.com campaign data; pre-pick one chart from /2026midterms (Mission's Dec 12 runoff is a natural tie-in). No data was pulled for this sample."],
   follow=_d["follow"],
   transitions=["One flipped district, one runoff, one tax break: put them together and what's the Valley telling Austin? Speaking of who decides, school boards are next.", "Elections come down to who shows up. The same is true at your school board."],
   links=_d["links"] + [l for l in _hw["links"] if l["label"] == "Politiquera"], confirm=_d["confirm"] + ["Choose the Politiquera data point"])

_e = OLD["E"]
_schoolish = ("CISD", "ISD", "Edinburg Advocate", "PSJA")
nb(id="E-school-boards", letter="E", title="School Boards", short="School Boards", subject="Trustees, budgets and board votes: Edinburg CISD, PSJA ISD, McAllen ISD",
   minutes=5, flex=True, trim_to=3, stretch_to=7, color="#2a9d8f",
   headlines=_e["headlines"][:2], chyrons=oc("E", ["e1", "e2"]),
   talking=[_e["talking"][0], "WEAVE-IN: this is a natural place for a Family & kids moment (screens and AI in class: PSJA's AI guidebook; Texas phones-off-during-the-school-day rule, HB 1481)."],
   follow=[f for f in _e["follow"] if "trustee" in f or "district" in f or "stop-loss" in f],
   transitions=["Two school boards' worth of decisions land on our kids. Now the folks who run the cities.", "Every campaign promise has a kid somewhere in it. Let's go from the classroom to City Hall."],
   links=[l for l in _e["links"] if any(k in l["label"] for k in _schoolish)], confirm=[c for c in _e["confirm"] if "ISD" in c or "CISD" in c], weave="Kids item: AI/screens in class (weave from H)")

_f = OLD["F"]
nb(id="F-city-hall", letter="F", title="City Hall", short="City Hall", subject="Mayors, councils and city managers: McAllen, Brownsville, Mission, Pharr; the Zoho park rezoning",
   minutes=5, flex=True, trim_to=3, stretch_to=7, color="#bc6c25",
   headlines=_e["headlines"][2:] + _f["headlines"][:1], chyrons=oc("F", ["e3", "e4", "f1"]),
   talking=_e["talking"][1:] + ["ZOHO AND THE PARK (menu item, folded in from the old Zoho block): " + _f["talking"][0], _f["talking"][1]],
   follow=[f for f in _e["follow"] if "officials" in f][:0] + _f["follow"] + ["Questions for officials: why a revolving door at the top, and what does it cost residents?"],
   transitions=["Forget the press release for a second: what does this change for somebody's Tuesday?", "City halls make deals. Let's talk about the deals that are supposed to bring jobs."],
   links=[l for l in _e["links"] if not any(k in l["label"] for k in _schoolish)] + _f["links"],
   confirm=[c for c in _e["confirm"] if "ISD" not in c] + _f["confirm"])

_g = OLD["G"]
nb(id="G-economic-development", letter="G", title="Economic Development", short="Econ Dev", subject="Jobs, projects and deals: McAllen EDC, the SpaceX data center abatement, Texas A&M McAllen, power and pipes",
   minutes=6, flex=True, trim_to=4, stretch_to=8, color="#43aa8b",
   headlines=_g["headlines"] + ["Hidalgo County can't block data centers outside city limits"], chyrons=oc("G", ["g1", "g2", "g3", "g4", "b2"]),
   talking=_g["talking"] + ["STARBASE / SPACEX ITEM (folded in from the old Starbase block): the $24B data center asked for a 10-year, 100% tax abatement; the county said no to a hearing, 3-2 (details in C). Ask: is this 'jobs for infrastructure', and who negotiates it? SpaceX also pledged $220M for Brownsville water projects.",
            _hw["talking"][1]],
   follow=_g["follow"] + ["If you could attach one condition to a data center in the Valley (jobs, water, power or internet), which?"],
   transitions=_g["transitions"] + ["Both sides said they're for the Valley. Let's find out what 'for the Valley' costs and who's paying."],
   links=_g["links"] + [l for l in _hw["links"] if "Daily McAllen" in l["label"]], confirm=_g["confirm"])

_c3, _l = OLD["C"], OLD["L"]
nb(id="H-family-kids", letter="H", title="Family & Kids (woven in)", short="Family+Kids", subject="NOT a dedicated segment: a light, woven-in moment with Jess after the local blocks and before state. How We'd Talk to Our Kids lives here",
   minutes=6, flex=True, trim_to=3, stretch_to=10, jess=True, signature=True, recurring=True, color="#8e6bbf",
   headlines=_c3["headlines"][:2] + ["How We'd Talk to Our Kids: strangers online, and when the group chat turns mean"],
   chyrons=oc("H", ["l1", "l2", "l3", "l4", "c2", "c3"]),
   talking=["WOVEN, NOT A SEGMENT: Jess joins for a light moment after the local blocks. Tag any kids item in B-F as 'weave into C-G' and drop it in wherever it fits (school boards: AI and phones in class; City Hall: parks and youth; Econ dev: jobs a kid can stay for). If the show runs long, this shrinks to 3 min; it stretches to 10 when a listener story lands."] + _c3["talking"][:3] + [t for t in _l["talking"][1:] ],
   follow=_c3["follow"] + _l["follow"],
   transitions=["Texas already bans phones during the school day. So what happens at 3:15 PM? Jess, that one's yours.", "Thanks, Jess. That's the family side. Now, what's Austin up to?"],
   links=_c3["links"] + _l["links"], confirm=_c3["confirm"] + _l["confirm"],
   weave="Tag kids items in C-G as 'weave into C-G' (see each block); Jess drops in here or anywhere they fit")

nb(id="I-statewide", letter="I", title="Statewide", short="Statewide", subject="Texas and Texas politics: the packet's Texas items, r/Texas top posts, Austin",
   minutes=4, flex=True, trim_to=2, stretch_to=6, color="#577590",
   headlines=[t["title"] for t in _texas[:3]] or ["Texas headlines from the packet"],
   chyrons=cy("I", [("Statewide", "Texas news & Texas politics")] + [((t.get("short") or t["title"])[:58], (t.get("source", "").split(" · ")[0] or "Texas")[:58]) for t in _texas[:2]] + [(OLD["H"]["chyrons"][2]["primary"], OLD["H"]["chyrons"][2]["secondary"])]),
   talking=["TEXAS ITEMS: use the packet's Texas headlines (listed in the Headlines section; each has a source link): " + "; ".join(t["title"] for t in _texas[:3]) + ".",
            "r/Texas: pull 2-3 top posts (Top, Past Week) that match local and Texas-wide politics, controversies or kids/digital topics; read the title and say why it matters. PREP Sunday night.",
            "BRIDGE FROM LOCAL: \"This is a Valley story, but Austin is already writing the rules.\" TEXAS GRID: ~98 GW now, ~100 GW more slated by end of 2027 (Daily McAllen Nov 17). The Ten Commandments classroom law is also a Texas story (see the National Desk item).",
            "Gov.-elect Hinojosa has promised to freeze new data-center development and takes office in January (details in Block C notes). CONFIRM before saying anything beyond that."],
   follow=["What is the one Texas story that actually changes something for a Valley family this month?"],
   transitions=["That's Texas. Now zoom out: what's the rest of the country arguing about?", "Austin writes the rules; Washington argues about them. Here's the national picture."],
   links=[{"label": t["title"][:80], "url": t["url"]} for t in _texas[:3] if t.get("url")], confirm=["Pull live r/Texas top-of-week titles", "Re-check Texas items Sunday night"])

_n = OLD["I"]
nb(id="J-national-desk", letter="J", title="The National Desk (+ Trending)", short="National", subject="Big national stories with a Valley angle (fact, then take, then 'why it matters here'), plus Trending: Wait, Don't Tell Me as riff material",
   minutes=8, flex=True, trim_to=6, stretch_to=10, color="#6d597a",
   headlines=_n["headlines"] + ["Trending: pick 1 to 3 'wait, don't tell me' stories"],
   chyrons=oc("J", ["i1", "i2", "i3", "i4", "i5", "i6", "h0"]),
   talking=_n["talking"] + [_hw["talking"][0] + " (flex: this is riff material inside the National Desk, not a separate block)"],
   follow=_n["follow"] + _hw["follow"][:1], transitions=["Okay, that's the 30,000-foot view. Now, what does it mean at 1,000 feet over the Valley?", "Okay, that's what the internet is losing its mind over this morning. Now it's your turn."],
   links=_n["links"], confirm=_n["confirm"])

_j = OLD["J"]; _m = OLD["M"]
nb(id="K-listener-line", letter="K", title="Listener Line", short="Listeners", subject="Call-ins and topic submissions (from submissions.md / call-ins.md); still no phone number",
   minutes=3, flex=True, trim_to=2, stretch_to=4, color="#f4a261",
   headlines=_j["headlines"], chyrons=oc("K", ["j1", "j2", "j3"]),
   talking=_j["talking"] + [_m["talking"][1]],
   follow=_j["follow"], transitions=["We've talked a lot. Now it's your turn: what are you hearing?", "Let's lighten up and see what the kids are saying."],
   links=_j["links"], confirm=_j["confirm"])

_k = OLD["K"]
nb(id="L-meme-close", letter="L", title="Meme of the Week & Close", short="Meme+Close", subject="What the kids are talking about (elementary, middle, high school; for parents), then the look-ahead and sign-off with Jess",
   minutes=4, flex=True, trim_to=3, stretch_to=6, jess=True, color="#ff7f50",
   headlines=_k["headlines"] + _m["headlines"], chyrons=oc("L", ["k1", "k2", "k3", "m2", "m3", "m5"]),
   talking=_k["talking"] + [_m["talking"][0], _m["talking"][2]],
   follow=_k["follow"], transitions=["That's the fun stuff. Thanks for spending the hour with us. See you next time.", "Jingle out."],
   links=_k["links"] + _m["links"], confirm=_k["confirm"] + _m["confirm"])

B[:] = NB
assert [b["letter"] for b in B] == list("ABCDEFGHIJKL")
for b in B: b.setdefault("short", b["title"].split(":")[0][:12])

# ---- compute ranges
def hhmm(m): return f"8:{m:02d}" if m < 60 else f"9:{m-60:02d}"
t = 0
for b in B:
    b["offset"] = t; b["start"] = hhmm(t); t += b["minutes"]; b["end"] = hhmm(t)
    b["timeRange"] = f"{b['start']}–{b['end']}"
assert t == 60, t
for b in B:
    for c in b["chyrons"]:
        assert len(c["primary"]) <= LEN and len(c["secondary"]) <= LEN, (c, len(c["primary"]), len(c["secondary"]))

ADJ = {  # a segue between every adjacent pair of blocks (the menu's default flow)
 ("A","B"): ["Quick check-in on what I've been up to this week, then we jump into the Valley.", "Before the news, a little of what Jess and I have been up to."],
 ("B","C"): ["Okay, enough about me. Let's get into the Valley.", "That's my week. Here's what the Valley's been up to."],
 ("C","D"): ["That's the headline. Now let's talk about the people who decide: the politics behind it.", "Hold that thought: that vote is local politics. Let's go there."],
 ("D","E"): ["We just watched an election come down to turnout. The same is true at your school board.", "Elections come down to who shows up. Let's go from the ballot box to the classroom."],
 ("E","F"): ["Two school boards' worth of decisions land on our kids. Now the folks who run the cities.", "From the classroom to City Hall: who's actually running the place?"],
 ("F","G"): ["City halls make deals. Let's talk about the deals that are supposed to bring jobs.", "Forget the press release for a second: what does this change for somebody's Tuesday?"],
 ("G","H"): ["A $225 million plant means 500 jobs on paper. Let's talk about what a good job does for a family dinner table.", "Great, we're growing. Can a kid who grows up here afford to stay? Jess, come on in."],
 ("H","I"): ["Thanks, Jess. That's the family side. Now, what's Austin up to?", "That's the kitchen-table view. Now the view from the Capitol."],
 ("I","J"): ["That's Texas. Now zoom out: what's the rest of the country arguing about?", "Austin writes the rules; Washington argues about them. Here's the national picture."],
 ("J","K"): ["Okay, that's the 30,000-foot view. Now it's your turn: what are you hearing?", "We've talked a lot. Now it's your turn."],
 ("K","L"): ["Let's lighten up and see what the kids are saying.", "That's the fun stuff. One more thing before we go: what the kids are talking about."],
}
NAMES = {b["letter"]: b["title"] for b in B}
JUMPS = [  # menu jumps: Drew can move through the blocks in any order
 ("any local block","Family & Kids","Strip out the politics: what does this change for one family? Jess, you're up."),
 ("Local News","Local Politics","Let's stay on this one a minute. Here's what I'd ask the people who decide."),
 ("any block","Economic Development","Forget the politics for a second: who gets the jobs, and who pays?"),
 ("Statewide","Local Politics","This is a Valley story, but Austin is already writing the rules."),
 ("National Desk","any local block","Strip out the politics: what did that story change for somebody at MFE or HRL this week?"),
 ("National Desk","any local block","Everybody's talking about it in Washington. Here's how it lands in Weslaco."),
 ("National Desk","Trending","Okay, that's the news. Here's what the internet is losing its mind over. Wait, don't tell me."),
 ("any block","Listener Line","We could go all morning on this, but let's hear from you: what are you seeing?"),
 ("any block","Meme of the Week","Let's lighten up and see what the kids are saying."),
 ("Meme of the Week","Family & Kids","That's the fun stuff. Now the part other parents skip."),
 ("Family & Kids","Listener Line","If one of those hit home, send us your story or your question. Anonymous is fine."),
 ("any block","next block","We could go all morning on this, but there's more Valley to cover."),
 ("Cold Open","What I've Been Up To","Quick check-in on what I've been up to this week, then we jump into the Valley."),
]
NEW_SEGUES = []

def build():
    path = os.path.join(ROOT, "obs-data.json")
    old = json.load(open(path))
    segs = []
    for i, b in enumerate(B):
        segs.append({
            "id": b["id"], "order": i, "suggestedOrder": i, "letter": b["letter"],
            "start": b["start"], "end": b["end"], "timeRange": b["timeRange"],
            "offsetMinutes": b["offset"], "shortName": b["short"], "weave": b.get("weave"),
            "durationMinutes": b["minutes"], "title": b["title"], "subject": b["subject"],
            "flex": b["flex"], "canTrimToMinutes": b.get("trim_to"), "canStretchToMinutes": b.get("stretch_to"),
            "jessDropIn": b.get("jess", False), "recurring": b.get("recurring", False), "signature": b.get("signature", False),
            "color": b["color"], "headlines": b["headlines"], "chyrons": b["chyrons"],
            "talkingPoints": b["talking"], "followUpQuestions": b["follow"], "transitionLines": b["transitions"],
            "links": b["links"], "needsVerification": b["confirm"]})
    segues, n = [], 0
    for (a, c), ls in ADJ.items():
        for l in ls:
            n += 1; segues.append({"id": f"sg{n:02d}", "kind": "adjacent", "fromLetter": a, "toLetter": c, "from": NAMES[a], "to": NAMES[c], "line": l})
    for a, c, l in JUMPS:
        n += 1; segues.append({"id": f"sg{n:02d}", "kind": "jump", "from": a, "to": c, "line": l})
    old["schemaVersion"] = 4
    old["chyronMaxChars"] = LEN
    old["schemaNotes"] = "v4 (Nov 18): 12 blocks A-L (new B = What I've Been Up To, family & kids woven into H, Starbase/Zoho/trending folded into other blocks). Segments carry offsetMinutes from the planned 8:00 start. coldOpen, jingle and upTo are filled by packet/build_packet.py on every build."
    old.setdefault("coldOpen", ""); old.setdefault("jingle", {}); old.setdefault("upTo", {})
    old["generated"] = "2026-11-18"
    old["show"]["runtimeMinutes"] = 60
    old["show"]["format"] = "open-format menu of story blocks; full 60-minute plan with suggested time ranges; blocks can be reordered, trimmed or stretched ('flex')"
    old["show"]["tickerHeadlines"] = [
        "Cameron County rejects SpaceX data center tax break hearing, 3-2",
        "FAA nationwide ground stop Nov. 13; Valley airports issued advisories",
        "DHS Sec. Mullin testifies on outages and LSU-Texas flight",
        "SNL: Mulaney best of season; 'Sister' sketch hits 5.8M views",
        "Bobby Pulido defeats Rep. Monica De La Cruz in TX-15",
        "Mission mayor runoff Dec. 12: Rick Salinas vs. Norie Gonzalez Garza",
        "FAA comments on up to 456 Starship launches close Dec. 7",
        "McAllen Food Truck Park closure delayed to Jan. 14, 2027",
        "USDA confirms another screwworm case in Starr County",
        "Need help? Call or text 988 any time"]
    old["show"]["socials"]["showEmail"] = EMAIL_FLAG
    old["segments"] = segs
    old["segues"] = segues
    p = old["principles"]
    p["format"] = ("Open format, not rigid segments. Full 60-minute plan; the extra time deepens segments (local politics, National Desk, "
                   "How We'd Talk to Our Kids, listener moments) rather than padding. Blocks can be reordered; 'flex' blocks can be trimmed or stretched.")
    p["themes"] = ["Local politics: races, school boards, mayors, city managers", "Economic development", "McAllen / RGV news",
                   "Controversial local stories (tax abatements, park land, SpaceX)", "The National Desk: big national stories with a Valley angle (Stern/K-Rock-style fact + take; always smaller than local)",
                   "Kids and the digital generation; Meme of the Week", "How We'd Talk to Our Kids (signature, recurring)", "Listener lines (DMs, email; no phone number)"]
    p["rules"] = ["Never state anything unverified; mark CONFIRM BEFORE AIR", "Say 988 whenever suicide or self-harm comes up",
                  "Jess: joins for the woven Family & Kids moment (Block H) and the close (Block L); anywhere else she drops in is ad lib",
                  "No core/skippable split: every block has a suggested time range; 'flex' blocks may be trimmed (see canTrimToMinutes) or stretched when the story runs long",
                  "National Desk stays smaller than local (6 min of 60; about 25% of the packet page at most)",
                  "No call-in phone number is announced; point to DMs and ditm@drewlentz.com (CONFIRM BEFORE AIR)",
                  "Chyrons max 60 characters"]
    p.pop("skippableMinutes", None)
    p["totalMinutes"] = sum(b["minutes"] for b in B)
    p["flexMinutes"] = sum(b["minutes"] for b in B if b["flex"])
    p["flexNote"] = "'flex' = can trim or stretch; replaces the old core/skippable split."
    old["callIns"]["channels"][0]["address"] = "ditm@drewlentz.com"
    old["callIns"]["channels"][0]["status"] = "seen as show inbox in Gmail; CONFIRM BEFORE AIR that it is intended for public submissions"
    json.dump(old, open(path, "w"), indent=2, ensure_ascii=False)
    return old

def md(old):
    o = []
    A = o.append
    A("# DREW IN THE MORNING — MONDAY 60-MINUTE RUN OF SHOW (open-format menu)")
    A("**Monday, November 23, 2026 · 8:00–9:00 AM CT · Live (Restream → YouTube / Facebook / Instagram / TikTok)**")
    A("Host: Drew Lentz · Jess: recurring guest (Family & Kids, Block H, and the close, Block L; she can drop in anywhere)\n")
    A("## How to use this")
    A("- **Full hour, no rush.** Most listeners stay the whole show, so the plan adds depth instead of padding: a quick personal check-in (B), local news, politics, school boards, City Hall and economic development, a woven-in **Family & Kids** moment with Jess (the How We'd Talk to Our Kids topics), Statewide, the National Desk with Trending as riff material, a listener line, and the Meme of the Week close. Times add up to exactly **60 minutes as planned**.")
    A("- **Open format.** Reorder blocks as the conversation flows. Blocks marked **FLEX** can be trimmed (see 'can trim to') when a story runs long, or stretched when it's hot. There is no 'core vs skippable' split anymore.")
    A("- **Local first.** The National Desk and Trending (J, 8 min, stretch to 10) stay clearly smaller than the local blocks (C–G ≈ 30 min).")
    A("- **Fact rules.** Facts were checked Nov 18 against pages opened that day (sources under each block; full list in `research.md` §10 and the packet). Anything unconfirmed is **CONFIRM BEFORE AIR**. Re-check Sunday night, Nov 22.")
    A("- **Sensitive topics:** whenever suicide, self-harm or sextortion comes up, say **988** (call or text, or chat at 988lifeline.org); 911 if someone is in immediate danger.")
    A("- **Listeners:** no call-in phone number exists, so don't announce one. Point to DMs on the show accounts (IG/TikTok @drewinthemorning) and **ditm@drewlentz.com — CONFIRM BEFORE AIR** that it's for public submissions. A Restream guest link is unverified.\n")
    A("## Show clock (60 min)")
    A("| Block | Time range | Min | Flex (trim to / stretch to) |")
    A("|---|---|---|---|")
    for b in B:
        fx = f"**FLEX** ({b.get('trim_to')}–{b.get('stretch_to')} min)" if b["flex"] else "fixed"
        extra = " · SIGNATURE, RECURRING" if b.get("signature") else ""
        jess = " · Jess" if b.get("jess") else ""
        A(f"| {b['letter']} · {b['title']}{extra}{jess} | {b['timeRange']} | {b['minutes']} | {fx} |")
    A(f"| **Total** | 8:00–9:00 | **60** | flex blocks total {sum(b['minutes'] for b in B if b['flex'])} min |\n")
    A("**If a story runs long:** borrow from F, G, I or E first (then D, then J). **If the show is short on news:** stretch C or D, or let H (Family & Kids) breathe to 10 min. Block B (What I've Been Up To) is 2 to 3 min: trim to 2 if the news is hot.\n---")
    for b in B:
        flex = f"FLEX: trim to {b.get('trim_to')} / stretch to {b.get('stretch_to')} min" if b["flex"] else "fixed"
        tag = " — SIGNATURE · RECURRING" if b.get("signature") else ""
        A(f"## {b['letter']} · {b['title'].upper()} ({b['timeRange']}, {b['minutes']} min){tag}")
        A(f"*{flex}. {b['subject']}*")
        A("")
        A("**Talking points**")
        for x in b["talking"]: A(f"- {x}")
        if b["follow"]:
            A("\n**Follow-up questions**")
            for x in b["follow"]: A(f"- {x}")
        if b["transitions"]:
            A("\n**Transition lines**")
            for x in b["transitions"]: A(f"- \"{x}\"")
        A("\n**Chyrons (≤60 chars)**")
        for c in b["chyrons"]: A(f"- {c['primary']} / {c['secondary']}")
        if b["links"]:
            A("\n**Sources / links**")
            for l in b["links"]: A(f"- {l['label']}: {l['url']}")
        if b["confirm"]:
            A("\n**CONFIRM BEFORE AIR:** " + "; ".join(b["confirm"]))
        A("\n---")
    A("### Producer notes")
    A("- **What changed (Nov 18, 5th update):** flowing 12-block open-format menu in this order: A Cold open + jingle · B What I've Been Up To · C Local news · D Local politics · E School boards · F City hall · G Economic development · H Family & kids (woven in, with Jess) · I Statewide · J National Desk (+ Trending) · K Listener line · L Meme of the Week / close. The dedicated Starbase, Zoho and open-format blocks are gone: Starbase/SpaceX items live in Local news and Economic development, Zoho lives in City hall, Trending sits inside the National Desk as riff material. Times total exactly 60 min. Segues exist between every adjacent pair plus jump lines (segues.md).")
    A("- **Thanksgiving week:** Nov 26 is Thanksgiving; expect lighter turnout and slower news.")
    A("- **Sunday-night checklist:** refresh headlines (KRGV, MyRGV, ValleyCentral, Daily McAllen); clear the CONFIRM items; pull Reddit top posts; read new DMs/email submissions; load `obs-data.json`; open the studio packet page.")
    A("- **Do not air** anything from personal/family, financial, client or legal email.")
    open(os.path.join(ROOT, "run-of-show-monday.md"), "w").write("\n".join(o) + "\n")

def side_files(old):
    groups = {}
    for s in old["segues"]:
        groups.setdefault((s["from"], s["to"]), []).append(s["line"])
    o = ["# Drew in the Morning — Segue Pool", "",
         "Natural on-air lines for blending between story types (open format). Use as is or in your own words. Numbers/facts in lines come from `research.md` §10 and the run of show.", "",
         "**Tip:** grab the bridge, then say the *so what* in your own words: local → why it matters → bigger picture. The pool now includes National Desk → local, listener-line, and Meme of the Week transitions for the 60-minute plan.", ""]
    n = 0
    for (a, c), ls in groups.items():
        o.append(f"## {a} → {c}")
        for l in ls:
            n += 1; o.append(f'{n}. "{l}"')
        o.append("")
    o += ["## Bigger-picture pivot cheat sheet",
          "- Local → state: \"This is a Valley story, but Austin is already writing the rules.\"",
          "- Local → national: \"Everybody's arguing about [AI / data centers / flights / kids and screens]. Here's what it looks like from McAllen.\"",
          "- National → local: \"That's the 30,000-foot view. Now, what does it mean at 1,000 feet over the Valley?\"",
          "- Local → human: \"Strip out the politics: what does this change for one family?\"",
          "- Local → future: \"In five years, what will we wish we'd asked this week?\"", ""]
    open(os.path.join(ROOT, "segues.md"), "w").write("\n".join(o))
    pr = old["principles"]
    sp = ["# Drew in the Morning — Show Principles", "",
          "## Format: open, full 60 minutes",
          "- Monday 8 AM CT, 60 minutes, live from McAllen. Drew talks about what is happening in his local universe (McAllen / Rio Grande Valley) and what it means in the larger picture.",
          "- The run of show (`run-of-show-monday.md`) is a **menu of story blocks** with a suggested time range for each; the ranges add up to exactly 60 minutes. Reorder, merge or stretch blocks as the conversation goes.",
          "- **No more core/skippable split.** Most listeners stay the whole hour, so the added time *deepens* segments (local-politics deep dives, the National Desk, How We'd Talk to Our Kids, listener moments) rather than padding. Blocks marked **FLEX** can be trimmed if a story runs long, or stretched.",
          "- Always keep: the Cold open (A), Local news (C), the woven Family & Kids moment (H, even if it shrinks to 3 min) and the close (L). Everything else is a menu: trim, skip, reorder or stretch as the conversation goes.",
          "- Use `segues.md` to move between blocks: local → why it matters → bigger picture.", "",
          "## Themes (what Drew watches)"] + [f"{i}. {t}" for i, t in enumerate(pr["themes"], 1)] + [
          "", "## National Desk rules",
          "- 3-5 big national stories a week, each with a one-line fact, a conversational Stern/K-Rock-style angle (fair, a little opinionated, flagged as opinion), and a 'why it matters in the Valley' line.",
          "- Always smaller than local: 6 min of 60 on air (stretch to 8) and no more than about a quarter of the packet page.",
          "", "## Tone", "- Open, honest, frank, practical. Not preachy. No judgment.", "- Local first, then the bigger picture.", "- Opinion is labeled as opinion. Facts come from the sources in `research.md` and the packet.", "",
          "## Rules"] + [f"- {r}" for r in pr["rules"]] + [
          "", "## Watchlist (feeds the weekly research pass)", "local political races · school boards · mayors and city managers · economic development · controversial local stories (tax abatements, park donations, SpaceX) · hard-to-talk-about parenting and digital topics for a 10- and 14-year-old · big national stories with a Valley angle (flights/FAA, DHS and Congress, culture moments like SNL)", ""]
    open(os.path.join(ROOT, "show-principles.md"), "w").write("\n".join(sp))

if __name__ == "__main__":
    old = build(); md(old); side_files(old)
    print("blocks", len(B), "minutes", t, "segues", len(old["segues"]))
