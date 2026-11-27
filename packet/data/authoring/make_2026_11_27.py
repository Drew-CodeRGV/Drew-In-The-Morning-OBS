import json
P='/workspace/drew-in-the-morning/packet/data/'
d=json.load(open(P+'packet-2026-11-26.json'))
d['meta'].update({"date":"2026-11-27","title":"Drew in the Morning \u00b7 Daily Briefing","dataAsOf":"Nov 27, 2026, 6:30 AM CT",
 "recap":"Last 24 hours (Nov 26-27, Thanksgiving to Black Friday), story bank for Monday Nov 30","mode":"daily","showDate":"2026-11-30","sample":False,
 "dateLabel":"Friday, November 27, 2026",
 "kidsTopic":"Screens vs. dice: parent groups are using Dungeons & Dragons as a screen-free hobby for 9- to 12-year-olds (NPR, Nov 27). Ask the 10-year-old what character they'd play; ask the 14-year-old whether a no-phones game night would actually work at our house"})
def H(title,short,url,source,pub,tldr,riff,hook,energy,valley=True,confirm=None,teaser=None,noprint=False,theme=None):
    it={"title":title,"short":short,"url":url,"source":source,"published":pub,"valley":valley,"tldr":tldr,"riff":riff,"hook":hook,"energy":energy,"links":[]}
    if confirm: it["confirm"]=confirm
    if teaser: it["teaser"]=teaser
    if noprint: it["noprint"]=True
    if theme: it["theme"]=theme
    return it
K="https://www.krgv.com/news/"
WN="https://wirelessnerd.net/2026/11/26/hidalgo-county-s-rural-wi-fi-went-dark-because-nobody/"
rgv=[
H("Harlingen dancers in NYC scramble to raise extra funds after weather postpones Macy's Thanksgiving Day Parade","Harlingen dancers stuck in NYC need $800 each",K+"harlingen-dancers-in-nyc-scramble-to-raise-extra-funds-after-weather-postpones-macy-s-thanksgiving-day-parade","KRGV \u00b7 Nov 26","2026-11-26",
 "After bad weather pushed the 100th Macy's Thanksgiving Day Parade to Saturday, 16 dancers from Harlingen's Monarch Dance Studio and their families are scrambling to raise at least $800 each to cover extra hotel and flight costs in New York. Director April Perez said each dancer had already raised $5,000 for the original trip.",
 "Pearland raised $350K in a few hours. Valley, our 16 Harlingen dancers need about $800 apiece. We can do this.",
 "16 Harlingen dancers made it to Macy's 100th parade. Now they need $800 each to stay until Saturday",5,teaser="Harlingen dancers stuck in New York",
 confirm="Check the studio's official donation link and whether the goal is already met before air"),
H("'What a wonderful surprise': Rio Grande Valley family welcomes Thanksgiving baby","Thanksgiving baby arrives in Edinburg",K+"what-a-wonderful-surprise-rio-grande-valley-family-welcomes-thanksgiving-baby","KRGV \u00b7 Nov 26","2026-11-26",
 "Baby Adrian, due Dec. 23, arrived early Thanksgiving morning by C-section at South Texas Health System Edinburg, weighing 6 pounds, 9 ounces. He is the Bazaldua family's fifth child, the only baby born there Thanksgiving morning, and shares a Thanksgiving birthday with his charge nurse, Amanda Marinez.",
 "Nearly a month early and right on time for pie. And the nurse shares his birthday? Come on.",
 "Due Dec. 23, he showed up Thanksgiving morning, and shares a birthday with his nurse",5,teaser="the Thanksgiving baby"),
H("'A place at the table': McAllen man hosts second annual free Thanksgiving dinner at Flying Walrus","McAllen man cooks free Thanksgiving meals",K+"a-place-at-the-table-mcallen-man-hosts-second-annual-free-thanksgiving-dinner-at-flying-walrus","KRGV \u00b7 Nov 26","2026-11-26",
 "McAllen resident Steven Guerrero spent nearly $600 of his own money and about 10 hours cooking for his second annual 'No One Should Miss Thanksgiving' meal giveaway at the Flying Walrus, where his boss provided drinks and the space. He told KRGV his family relied on neighbors for Thanksgiving when he was growing up.",
 "Six hundred bucks of his own money and ten hours at the stove. That's the whole holiday in one guy.",
 "He grew up relying on neighbors for Thanksgiving. Now he spends $600 of his own to feed McAllen",5,teaser="the Flying Walrus Thanksgiving"),
H("Hidalgo County's Rural Wi-Fi Went Dark Because Nobody Budgeted to Keep it Alive","Hidalgo Co. rural Wi-Fi went dark",WN,"WirelessNerd via r/RioGrandeValley \u00b7 Nov 26","2026-11-26",
 "Hidalgo County's free rural Wi-Fi, built with COVID money, is off because the build was funded and the upkeep was not, WirelessNerd writes; by the author's count the equipment went about three years without maintenance. KRGV reported in 2025 the service had connected 130 colonias and LUPE pushed the county to restore it.",
 "Ribbon cuttings are free. Keeping the radios alive is the part nobody budgets. Full disclosure, this one's ours.",
 "Hidalgo County's free colonia Wi-Fi is dark: the build was funded, the upkeep never was",4,theme="RGV Tech",teaser="why the county Wi-Fi went dark",
 confirm="Opinion piece by WirelessNerd (Drew's brand; author discloses his company bid and came second). Disclose on air; county status from KRGV Sep 30, 2025"),
H("Cameron County commissioners pass resolution to protect public access to Boca Chica Beach","Cameron Co. resolution protects Boca Chica access",K+"cameron-county-commissioners-pass-resolution-to-protect-public-access-to-boca-chica-beach","KRGV \u00b7 Nov 26","2026-11-26",
 "Cameron County commissioners unanimously approved a resolution protecting Boca Chica Beach, public access to it and its wildlife and historic resources. It followed Texas Tribune reporting on SpaceX's proposal to buy Boca Chica State Park; Gov.-elect Gina Hinojosa directed state officials to pause sale discussions during her transition.",
 "The county put it in writing: the beach is the public's. SpaceX can want the park all it likes.",
 "Unanimous: Cameron County puts public access to Boca Chica Beach on the record",4,theme="RGV Tech",teaser="the Boca Chica beach vote",
 confirm="Article says the vote was 'Tuesday'; confirm the meeting date before air"),
H("SpaceX Seeks Greater Security Around Boca Chica Launch Facility","SpaceX: 1,200 acres for Boca Chica security",
 "https://texasborderbusiness.com/spacex-seeks-greater-security-around-boca-chica-launch-facility/","Texas Border Business \u00b7 Nov 26","2026-11-26T11:00:00-06:00",
 "SpaceX says its proposal to acquire about 1,200 acres of state-managed land around its Starship launch facility would improve public safety, strengthen security and permanently protect about 600 acres of coastal habitat. The company says unauthorized people regularly enter operational areas through Texas Parks and Wildlife land.",
 "Same land, two stories: SpaceX says security, the county says public access. Both landed this week.",
 "SpaceX wants 1,200 acres around Starbase and says it would protect 600 of them forever",4,theme="RGV Tech",
 confirm="Company's own framing via a Texas Border Business series; pair with the county resolution"),
H("SpaceX Transforms Texas Dirt Field into Massive AI Data Center in 90 Days","Starbase data center rises in 90 days","https://x.com/i/trending/2126209626958078202","X News \u00b7 Nov 27","2026-11-27",
 "Side-by-side aerial images shared on X from early September to late November show SpaceX's 444-acre site near the Port of Brownsville going from open land to a complex of white-roofed buildings and rows of Tesla Megapacks. It is part of the $24 billion supercomputing campus with an on-site natural gas plant.",
 "Ninety days, dirt to data center. Love it or hate it, nobody builds like that down here.",
 "Dirt field to AI data center in about 90 days: aerial photos show SpaceX's Brownsville build",4,theme="RGV Tech",
 confirm="X News summary of posts (photos, $250M battery estimate); confirm with local news before air"),
H("Angels of Love collecting old phones, electronics to provide free service for domestic violence survivors","Old phones \u2192 free service for DV survivors",K+"angels-of-love-collecting-old-phones-electronics-to-provide-free-service-for-domestic-violence-survivors","KRGV \u00b7 Nov 26","2026-11-26",
 "McAllen nonprofit Angels of Love is collecting used cellphones and electronics, which a third party refurbishes and recycles, so domestic violence survivors in its care get two months of free phone service. Drop-offs are at 1305 E. Nolana Ave., Suite D, in McAllen.",
 "That old phone in your junk drawer can be somebody's lifeline. Black Friday upgrade? Donate the old one.",
 "Upgrading on Black Friday? Your old phone can buy a survivor two months of free service",4,theme="RGV Tech",noprint=True),
H("Vigil held in Brownsville during John Allen Rubio's execution to honor children he killed","Brownsville vigil as Rubio executed",K+"vigil-held-in-brownsville-during-john-allen-rubio-s-execution-to-honor-children-he-killed","KRGV \u00b7 Nov 26","2026-11-26",
 "Community members and family gathered Thursday at Brownsville's Tres Angeles Park, built where the apartment once stood, to remember the three children John Allen Rubio killed in 2003 as his execution was carried out in Huntsville. 'It's done,' Cameron County DA Luis Saenz said.",
 "Twenty-three years. A quiet moment for that family and for Brownsville.",
 "Big one: Rubio executed for the 2003 killings; Brownsville gathers at Tres Angeles Park",2,
 confirm="Sensitive: do not name the children on air; keep it respectful"),
H("Hidalgo County 911 dispatchers stay busy on Thanksgiving Day as call volume rises","911 calls jump to ~450 on Thanksgiving",K+"hidalgo-county-911-dispatchers-stay-busy-on-thanksgiving-day-as-call-volume-rises","KRGV \u00b7 Nov 26","2026-11-26",
 "Hidalgo County Sheriff's Office dispatchers handle about 400 calls on a typical day and about 450 on Thanksgiving, with kitchen fires and domestic disturbances among the top calls, 13-year dispatcher Oren Cortez told KRGV. Fires from deep-frying turkeys and ovens are common.",
 "Fifty extra 911 calls and a lot of them are turkey fryers. Shout-out to the people answering.",
 "Thanksgiving pushes Hidalgo County 911 to about 450 calls, turkey fryers included",3,noprint=True),
H("First case of New World screwworm reported in Cameron County","Screwworm reaches Cameron Co.; 12 in RGV","https://myrgv.com/local-news/2026/11/25/first-case-of-new-world-screwworm-reported-in-cameron-county/","MyRGV \u00b7 Nov 25","2026-11-25T17:22:00-06:00",
 "Cameron County Judge Eddie Trevi\u00f1o Jr. said the Texas Animal Health Commission notified the county Tuesday that New World screwworm has arrived in the Lower Valley. That makes 12 confirmed Valley cases: eight in Starr, three in Hidalgo and one in Cameron.",
 "Pet owners: cover cuts and check your animals. This pest keeps moving east.",
 "Screwworm hits Cameron County: 12 Valley cases now, from Starr to the coast",3,
 confirm="Count from TAHC via MyRGV Nov 25; Facebook (ValleyCentral) chatter flagged it; recheck the total before air"),
H("Project Organic Opens New Opportunities for Businesses and Employment","Harlingen Project Organic: 500+ jobs",
 "https://texasborderbusiness.com/project-organic-opens-new-opportunities-for-businesses-and-employment/","Texas Border Business \u00b7 Nov 27","2026-11-27T05:00:00-06:00",
 "Project Organic, a planned 71-acre mixed-use development in Harlingen's Medical District, could hold more than 300,000 square feet of commercial space and generate more than 500 permanent jobs, HEDC CEO Orlando Campos said. First anchor tenant Garver Engineering opened a 25,000-square-foot office built for more than 100 workers.",
 "Five hundred jobs in the Medical District. Harlingen's quietly building something.",
 "Harlingen's Project Organic: 71 acres, 300,000 sq ft and 500-plus jobs planned",3,noprint=True),
H("Community resource boxes installed in Mercedes neighborhoods","Mercedes puts resource boxes in colonias",K+"community-resource-boxes-installed-in-mercedes-neighborhoods","KRGV \u00b7 Nov 26","2026-11-26",
 "The city of Mercedes and Mercedes ISD installed three community resource boxes in underserved neighborhoods and colonias, stocked with library books, GED and job application information, health materials and first-aid supplies. A fourth is planned by January 2027.",
 "A little free library with a job application and a Band-Aid. Simple and smart.",
 "Books, GED info and first aid: Mercedes puts resource boxes in its colonias",3,noprint=True),
H("73-year-old Pharr hotel employee recovering after assault caught on surveillance video","Pharr hotel worker, 73, assaulted",K+"73-year-old-pharr-hotel-employee-recovering-after-assault-caught-on-surveillance-video","KRGV \u00b7 Nov 26","2026-11-26",
 "Pharr police arrested a 37-year-old man Wednesday after surveillance video showed a 73-year-old hotel worker being hit outside a hotel near North Cage Boulevard and Nolana Avenue. The worker told KRGV he has neck pain and cannot work until he heals.",
 "Seventy-three and still working, and someone does this. Glad he's home.",
 "Developing: 73-year-old Pharr hotel worker hit on camera; arrest made",2,noprint=True),
H("Safety concerns prompt pedestrian study of busy crosswalk near UTRGV in Edinburg","TxDOT to study UTRGV crosswalk",K+"safety-concerns-prompt-pedestrian-study-of-busy-crosswalk-near-utrgv-in-edinburg","KRGV \u00b7 Nov 26","2026-11-26",
 "TxDOT will conduct a pedestrian safety study near UTRGV in Edinburg after state Rep. Terry Canales raised concerns about people crossing six-lane University Drive. Students told KRGV the crosswalk buttons sometimes don't work and they've seen close calls.",
 "Six lanes, a broken button and a scooter. Glad somebody's measuring it.",
 "Six lanes and a crosswalk button that doesn't always work: TxDOT will study UTRGV's crossing",3,noprint=True),
H("DPS: Mission man in custody after fleeing from deadly Thanksgiving Day crash","Mission crash: driver arrested after fleeing",K+"dps-mission-man-in-custody-after-fleeing-from-deadly-thanksgiving-day-crash","KRGV \u00b7 Nov 26","2026-11-26",
 "A 22-year-old Mission man was arrested on a charge of collision involving death after a crash on Moorfield Road north of 5 Mile Line at about 1:44 a.m. Thursday, DPS said. A 30-year-old rear passenger died at the scene; another passenger had minor injuries.",
 "Holiday weekend: slow down, and never leave the scene.",
 "Developing: driver arrested after fleeing a deadly Thanksgiving crash near Mission, DPS says",1,noprint=True),
]
tx=[
H("Texas band raises $350,000 to stay for delayed Macy's Thanksgiving parade: \"Outpouring of kindness\"","Pearland band raises $350K to stay in NYC",
 "https://www.cbsnews.com/news/macys-thanksgiving-parade-marching-bands-delay-cost/","CBS News \u00b7 Nov 26","2026-11-26T10:44:00-06:00",
 "Pearland High School's 500-member band raised $350,000 in a few hours to cover two extra hotel nights, meals and charter buses home after the Macy's parade moved to Saturday, director Ryan Demkovich told CBS News. Donors included Gringo's Mexican Kitchen, Mattress Mack and CenterPoint Energy.",
 "Three hundred fifty grand in a few hours. Texas doesn't let its band kids miss 34th Street.",
 "500 Texas band kids, $350,000 raised in hours: Pearland is marching in Macy's on Saturday",5,valley=False,teaser="the $350K band rescue",
 confirm="Top r/texas post Nov 26 (815 upvotes); confirmed by CBS News, KHOU, Click2Houston"),
H("Eckhardt, Huffines clash over Texas comptroller transition","Comptroller transition fight",
 "https://feeds.texastribune.org/link/16799/17540998/texas-comptroller-sarah-eckhardt-don-huffines-transition-co","Texas Tribune \u00b7 Nov 25","2026-11-25T16:30:00-06:00",
 "Democratic Comptroller-elect Sarah Eckhardt says she hasn't received documents or briefings she requested after defeating Don Huffines on Nov. 3. The Republican incumbent pushed back, saying the briefings are coming.",
 "The state's checkbook is changing hands and the handoff is already messy.",
 "Texas' new comptroller says she can't get the briefings; Huffines says they're coming",3,valley=False,noprint=True),
]
d['headlines']={'rgv':rgv,'texas':tx,'image':{"file":"assets/starship_thumb.jpg","caption":"File photo: Starship (Steve Jurvetson, CC BY 2.0, Wikimedia Commons)","credit_url":"https://commons.wikimedia.org/wiki/File:SpaceX_Starship_before_IFT-5.jpg","forItem":5}}
d['nationalDesk']=[
 {"id":"asylum-scotus","title":"Trump effectively ended asylum. Advocates look to the Supreme Court to restore it","print":True,
  "summary":"Nov 27: For nearly two years the administration has barred asylum claims at the U.S.-Mexico border and canceled thousands of pending applications; the Supreme Court will soon consider whether the president can unilaterally suspend asylum access (NPR).",
  "angle":"(Opinion) Whatever side you're on, 'can a president switch off a law Congress wrote' is the question, and it lands at the Court.",
  "valley":"Border Patrol apprehensions hit their lowest level in agency history this year, per NPR. The Valley sees both sides of this up close.",
  "links":[{"label":"NPR","url":"https://www.npr.org/2026/11/27/nx-s1-6037854/trump-effectively-ended-asylum-supreme-court"}],
  "teaser":"asylum heading to the Supreme Court","pfact":"SCOTUS to weigh Trump's border asylum ban.","pangle":"Can a president switch off asylum?","pvalley":"Record-low apprehensions here.",
  "hook":"Asylum at the border is all but gone, and the Supreme Court will decide if that's legal","energy":4},
 {"id":"storm-blackouts","title":"From Thanksgiving blackouts to Black Friday, a holiday hit by wild weather and economic woes","print":True,
  "summary":"Nov 27: A storm from the Midwest to Manhattan left more than 980,000 people without power at its peak, canceled 400-plus flights and delayed 2,000 more; Atlantic City saw 2 to 3 feet of water in low spots (NPR).",
  "angle":"(Opinion) Nearly a million people ate Thanksgiving by flashlight. Your dry turkey is fine.",
  "valley":"Valley airports ran on time; if family is flying home from the East Coast this weekend, check that connection.",
  "links":[{"label":"NPR","url":"https://www.npr.org/2026/11/27/nx-s1-6054884/thanksgiving-weather-black-friday"}],
  "teaser":"nearly a million in the dark on Thanksgiving","pfact":"980K lost power; 400+ flights canceled.","pangle":"Thanksgiving by flashlight.","pvalley":"Check East Coast connections.",
  "hook":"Nearly a million people lost power on Thanksgiving as a storm hammered the East","energy":4},
 {"id":"tariffs-14","title":"China and other US trading partners hit back at Trump's new tariff plans","print":True,
  "summary":"Nov 26: China, Japan and others protested planned U.S. tariff hikes on 14 economies over alleged excess factory capacity, announced Wednesday after a Section 301 probe and likely to take effect early next year (AP; Reuters).",
  "angle":"(Opinion) Round two of the tariff fight, right after the midterms. Your Christmas list notices before Washington does.",
  "valley":"Mexico is not on the list of 14 (Business Times list). Watch whether that pushes more trade through Valley bridges.",
  "links":[{"label":"AP","url":"https://apnews.com/article/us-tariffs-china-japan-singapore-b94a693004ad8f9b5e78f7aafb196a71"},{"label":"Reuters","url":"https://www.reuters.com/3fec1b0a85a0/world/china/us-proposes-new-tariffs-14-trading-partners-fight-excess-factory-capacity-2026-11-25/"}],
  "teaser":"the new tariff fight","pfact":"New tariffs on 14 economies; China pushes back.","pangle":"Round two, post-midterms.","pvalley":"Mexico not on the list.",
  "hook":"Fourteen economies, new tariffs, and China says the premise is false","energy":3,"confirm":"Valley bridge angle is our opinion, not reported"},
 {"id":"sheinbaum-dea","title":"Mexico's Sheinbaum slams U.S. DEA tip lines as interference","print":False,
  "summary":"Nov 26-27: President Claudia Sheinbaum called new DEA anonymous tip lines for Sinaloa residents (WhatsApp, Signal) interference, and also pushed for government talks on SpaceX launches after debris hit Tamaulipas beaches (X News summary).",
  "angle":"(Opinion) Anonymous tips by WhatsApp from a foreign agency. You can see why Mexico City bristled.",
  "valley":"Tamaulipas is next door, and the SpaceX debris complaint points straight at Boca Chica.",
  "links":[{"label":"X News","url":"https://x.com/i/trending/2125995650776994269"}],
  "teaser":"Sheinbaum vs. the DEA","pfact":"Sheinbaum: DEA tip lines are interference.","pangle":"Sovereignty fight.","pvalley":"SpaceX debris in Tamaulipas.",
  "hook":"Mexico's president calls DEA cartel tip lines interference, and brings up SpaceX debris on Tamaulipas beaches","energy":4,
  "confirm":"X News summary only; confirm with AP/Reuters before air"},
]
def T(i,title,cat,one,ang,url,src,short,teaser,hook,en,pr=False,confirm=""):
    return {"id":i,"title":title,"category":cat,"one_line":one,"suggested_angle":ang,"source_url":url,"source":src,"short":short,"teaser":teaser,"verified":True,"confirm":confirm,"print":pr,"links":[],"hook":hook,"energy":en}
d['trending']=[
 T("eagles-cowboys","Eagles rally to stun Cowboys coming back from 21 points behind","sports",
   "Down 31-10 early in the third, the Eagles beat Dallas 39-38 on Thanksgiving behind ex-Cowboys practice-squad QB Joe Milton (three TD passes, one TD run) and Jake Elliott's 59-yard field goal with 2 seconds left.",
   "The Cowboys' old backup comes home and beats them on Thanksgiving. You can't write it meaner.",
   "https://www.npr.org/2026/11/27/nx-s1-6055519/eagles-stun-cowboys","NPR (AP) \u00b7 Nov 27","Eagles stun Cowboys 39-38","the Cowboys collapse",
   "The Cowboys' former backup QB erased a 21-point lead and beat them 39-38 on a 59-yard kick",5,pr=True),
 T("tg-football","Bears outlast Lions 39-35; Bills beat Chiefs 13-10 on 57-yard field goal at the gun","sports",
   "Thanksgiving's other games: Chicago won a 39-35 shootout at Detroit, and Tyler Bass hit a 57-yard field goal as time expired to lift Buffalo past Kansas City 13-10 (ESPN scoreboard; AP).",
   "Three games, three finishes. Best Thanksgiving football day in years.",
   "https://www.espn.com/nfl/scoreboard/_/week/12/year/2026/seasontype/2","ESPN \u00b7 Nov 26","Bears 39-35; Bills walk-off","Thanksgiving football chaos",
   "A 39-35 shootout and a 57-yard walk-off: the rest of Thanksgiving football delivered too",4),
 T("bf-deals-meh","Black Friday 2026 deals draw mixed reactions online","shopping",
   "Online chatter Friday morning turned to complaints that discounts are smaller this year, even as U.S. online Black Friday spending is projected at $12.9 billion, up 9% (X News summary).",
   "Is it just us or are the deals kind of bad? Jess, what's in your cart?",
   "https://x.com/i/trending/2126272126134988985","X News \u00b7 Nov 27","'Do Black Friday deals suck?'","whether the deals are actually good",
   "Shoppers say the deals stink, but online Black Friday spending is still headed for $12.9 billion",4,pr=True,confirm="Spending projection from X News summary; confirm source (Adobe?) before air"),
 T("shopify-globe","Shopify launches a skate-park game around its live Black Friday sales globe","tech",
   "Shopify CEO Tobi L\u00fctke unveiled this year's live Black Friday Cyber Monday globe as a multiplayer skate-park game at bfcm.shop, showing sales in real time through the weekend (X News summary).",
   "Watching the whole world shop while doing a kickflip. Peak 2026.",
   "https://x.com/i/trending/2126158988886917484","X News \u00b7 Nov 27","Shopify's Black Friday skate park","the Black Friday skate park",
   "Shopify turned live Black Friday sales into a skate-park video game",3,confirm="X News summary; try bfcm.shop before air"),
 T("dnd-tweens","Screen-free tweens try their hand at Dungeons & Dragons","parenting",
   "NPR visited Tweens Without Screens, a New York parent collective whose monthly D&D groups for 9- to 12-year-olds are a screen-free alternative built on dice, imagination and talking face to face.",
   "Fifty years later, D&D is the parents' secret weapon. Who's the Dungeon Master at your house?",
   "https://www.npr.org/2026/11/27/nx-s1-6042445/screen-free-tweens-try-their-hand-at-dungeons-dragons","NPR \u00b7 Nov 27","D&D: the screen-free hack","D&D for screen-free kids",
   "Parents found a screen-time fix from 1974: Dungeons & Dragons",4),
 T("strobe-talbott","Strobe Talbott, former Time magazine reporter and deputy secretary of state, has died","news",
   "Strobe Talbott, a former Time magazine reporter who later served as deputy secretary of state, has died, NPR reports.",
   "A reporter who went on to run diplomacy. Quick tip of the hat.",
   "https://www.npr.org/2026/11/27/g-s1-155990/strobe-talbott-obit","NPR \u00b7 Nov 27","Strobe Talbott dies","Strobe Talbott",
   "Strobe Talbott, the Time reporter turned deputy secretary of state, has died",2,confirm="Only the headline was read; read before air"),
]
d['tech']={"origin":"wires","issue":None,"searchedAt":"2026-11-27T06:10:00-06:00",
 "note":"No Fast Company Daily issue found in the last 48 h: searched Drew's Gmail read-only on Nov 27, 2026 at 6:10 AM CT (drew@drewlentz.com, then drew@politiquera.com) for (from:fastcompany OR subject:\"Fast Company Daily\") newer_than:2d. RGV tech items come first from local outlets; national items are the fallback from the tech wires (The Verge, TechCrunch, Ars Technica).",
 "items":[
  {"id":"hidalgo-wifi-dark","title":"Hidalgo County's Rural Wi-Fi Went Dark Because Nobody Budgeted to Keep it Alive","short":"Hidalgo rural Wi-Fi went dark","source":"WirelessNerd (via r/RioGrandeValley)","source_url":WN,"published":"Nov 26",
   "one_line":"Hidalgo County's free colonia Wi-Fi, built with COVID money, is off because nobody funded the upkeep; the author says the gear went about three years without maintenance.",
   "angle":"Digital equity lesson for every Valley city: budget the long tail, not just the ribbon cutting. (Our own piece; disclose.)","hook":"Hidalgo County's free colonia Wi-Fi is dark: the build was funded, the upkeep never was","energy":4,"verified":True,"confirm":"Opinion piece by Drew's WirelessNerd; disclose on air","links":[],"basis":"WirelessNerd \u00b7 RGV Tech","valley":True},
  {"id":"starbase-dc-90","title":"SpaceX Transforms Texas Dirt Field into Massive AI Data Center in 90 Days","short":"Starbase DC rises in 90 days","source":"X News","source_url":"https://x.com/i/trending/2126209626958078202","published":"Nov 27",
   "one_line":"Aerial photos from September to late November show SpaceX's 444-acre Brownsville-area site turned into a data center complex with rows of Tesla Megapacks.",
   "angle":"The county said no to the tax break; the buildings went up anyway. Starbase's own abatement vote is Dec. 9.","hook":"Dirt field to AI data center in about 90 days near the Port of Brownsville","energy":4,"verified":True,"confirm":"X News summary; confirm with local news","links":[],"basis":"X News \u00b7 RGV Tech","valley":True},
  {"id":"boca-security","title":"SpaceX Seeks Greater Security Around Boca Chica Launch Facility","short":"SpaceX wants 1,200 acres","source":"Texas Border Business","source_url":"https://texasborderbusiness.com/spacex-seeks-greater-security-around-boca-chica-launch-facility/","published":"Nov 26",
   "one_line":"SpaceX says acquiring about 1,200 acres of state land around its launch site would improve safety and security and permanently protect about 600 acres of habitat; Cameron County just passed a resolution protecting public beach access.",
   "angle":"Security vs. public beach: the Boca Chica tug-of-war in one week.","hook":"SpaceX wants 1,200 acres around Starbase; the county says the beach stays public","energy":4,"verified":True,"confirm":"","links":[],"basis":"Texas Border Business \u00b7 RGV Tech","valley":True},
  {"id":"angels-phones","title":"Angels of Love collecting old phones, electronics to provide free service for domestic violence survivors","short":"Old phones for DV survivors","source":"KRGV","source_url":K+"angels-of-love-collecting-old-phones-electronics-to-provide-free-service-for-domestic-violence-survivors","published":"Nov 26",
   "one_line":"McAllen's Angels of Love trades donated phones and electronics for refurbishing so survivors get two months of free phone service.",
   "angle":"Black Friday upgrade? The old phone has a second job.","hook":"Upgrading on Black Friday? Your old phone can buy a survivor two months of service","energy":4,"verified":True,"confirm":"","links":[],"basis":"KRGV \u00b7 RGV Tech","valley":True},
  {"id":"nvidia-sea","title":"Nvidia hits pause on chip shipments to Southeast Asia","short":"Nvidia pauses SE Asia shipments","source":"TechCrunch","source_url":"https://techcrunch.com/2026/11/26/nvidia-hits-pause-on-chip-shipments-to-southeast-asia/","published":"Nov 26",
   "one_line":"Nvidia told manufacturing partners to pause server shipments to Malaysia, Singapore, Thailand and Indonesia as the U.S. tightens its push to keep AI chips out of China.",
   "angle":"The AI chip squeeze keeps tightening, the same week SpaceX's Valley data center is going up.","hook":"Nvidia pauses AI server shipments to four Southeast Asian countries","energy":3,"verified":True,"confirm":"Only the headline and deck were read","links":[]},
  {"id":"1password","title":"1Password said hackers broke into its internal systems, but customer passwords are safe","short":"1Password breached; vaults safe","source":"TechCrunch","source_url":"https://techcrunch.com/2026/11/25/1password-said-hackers-broke-into-its-internal-systems-but-customer-passwords-are-safe/","published":"Nov 25",
   "one_line":"The password manager said an attacker got into an employee's corporate account and took some customer information; customer passwords are safe.",
   "angle":"If the family uses 1Password: turn on two-factor and watch for phishing this week.","hook":"Hackers got into 1Password's internal systems; the company says your passwords are safe","energy":3,"verified":True,"confirm":"Only the headline and deck were read","links":[]},
 ]}
s=d['sports']
s['highSchool']['round']="Regional semifinals TODAY, Fri Nov 27: Edinburg Vela vs. Austin Westlake (2 p.m., Heroes Stadium, San Antonio), PSJA North vs. Dripping Springs (5 p.m., Alamo Stadium), La Villa vs. Falls City (6 p.m., Alice)"
s['highSchool']['sourceNote']="RGVSports playoff page (current at 6 AM CT Nov 27). No RGV playoff results since Saturday Nov 21; games are today, so no scores yet."
s['highSchool']['results']=[]
s['highSchool']['next']=[
 {"title":"RGV Football Playoff Schedule & Scores: Vela-Westlake 2 p.m., PSJA North-Dripping Springs 5 p.m., La Villa-Falls City 6 p.m.","short":"3 Valley teams play today","url":"https://www.rgvsports.com/rgv-football-playoff-schedule/","source":"RGVSports \u00b7 Nov 27"},
 {"title":"RGV high school football regional semifinal preview: Edinburg Vela Sabercats","short":"Vela: 0-2 vs. Westlake in round 3","url":K+"rgv-high-school-football-regional-semifinal-preview-edinburg-vela-sabercats","source":"KRGV \u00b7 Nov 26"}]
s['nfl']={"title":"NFL Thanksgiving: Bears 39-35 at DET, Eagles 39-38 at DAL, Bills 13-10 vs KC","scoreSource":{"title":"ESPN NFL scoreboard, Thu Nov 26","short":"","url":"https://www.espn.com/nfl/scoreboard/_/week/12/year/2026/seasontype/2","source":"ESPN"},
 "scores":[["Thu Nov 26","CHI 39, DET 35"],["Thu Nov 26","PHI 39, DAL 38"],["Thu Nov 26","BUF 13, KC 10"],["Wed Nov 25","LAR 26, GB 13"]],
 "notable":[{"title":"Eagles rally to stun Cowboys coming back from 21 points behind","short":"Ex-Cowboy Joe Milton beats Dallas","url":"https://www.npr.org/2026/11/27/nx-s1-6055519/eagles-stun-cowboys","source":"NPR (AP) \u00b7 Nov 27"}]}
n=s['nba']
n['scoreSource']={"title":"ESPN NBA scoreboard, Wed Nov 25 (no games Thanksgiving)","short":"","url":"https://www.espn.com/nba/scoreboard/_/date/20261125","source":"ESPN"}
n['scores']=[["Wed Nov 25","HOU 116, PHX 104"],["Wed Nov 25","POR 116, SA 111"],["Wed Nov 25","MIN 113, OKC 106"],["Wed Nov 25","NY 121, CLE 102"],["Wed Nov 25","GS 129, SAC 110"]]
n['texas']=[["Wed Nov 25","HOU 116, PHX 104"],["Wed Nov 25","POR 116, SA 111"]]
d['leads']=[]
d['chisme']={}
o=json.load(open('/tmp/obits.json')); d['obituaries']=o
for k in ['up_to','up_to_script','up_to_meta','up_to_coming']: d.pop(k,None)
json.dump(d,open(P+'packet-2026-11-27.json','w'),indent=1,ensure_ascii=False)
print('ok',len(rgv),len(tx))
