import json
P='/workspace/drew-in-the-morning/packet/data/'
d=json.load(open(P+'packet-2026-11-27.json'))
d['meta'].update({"date":"2026-11-28","title":"Drew in the Morning \u00b7 Daily Briefing","dataAsOf":"Nov 28, 2026, 6:45 AM CT",
 "recap":"Last 24 hours (Nov 27-28, Black Friday into Saturday), story bank for Monday Nov 30","mode":"daily","showDate":"2026-11-30","sample":False,
 "dateLabel":"Saturday, November 28, 2026",
 "kidsTopic":"Grand Theft Auto VI is everywhere: it launched Nov. 19 and a new 'Criminal Profile' system that tracks players' crime choices has gamers arguing online (X News summary, Nov. 26). Ask the 14-year-old what friends are saying about it; for the 10-year-old, a good moment to talk about which games are for grown-ups and why"})
def H(title,short,url,source,pub,tldr,riff,hook,energy,valley=True,confirm=None,teaser=None,noprint=False,theme=None):
    it={"title":title,"short":short,"url":url,"source":source,"published":pub,"valley":valley,"tldr":tldr,"riff":riff,"hook":hook,"energy":energy,"links":[]}
    if confirm: it["confirm"]=confirm
    if teaser: it["teaser"]=teaser
    if noprint: it["noprint"]=True
    if theme: it["theme"]=theme
    return it
K="https://www.krgv.com/news/"
VC="https://www.valleycentral.com/"
AJ="https://www.aljazeera.com/news/2026/11/26/mexico-seeks-us-talks-about-suspected-spacex-debris"
AP_ES="https://apnews.com/article/mexico-eeuu-spacex-cohetes-tamaulipas-b93da22b241e7261fe19caabe6ade8a6"
rgv=[
H("Marching On: La Villa holds off Falls City, advances to regional final","La Villa 42, Falls City 34: regional final!","https://rgvsports.com/marching-on-la-villa-holds-off-falls-city-advances-to-regional-final/","RGVSports \u00b7 Nov 27","2026-11-27T22:25:00-06:00",
 "La Villa beat Falls City 42-34 Friday night at Memorial Stadium in Alice in the Region IV-2A Division II semifinals, reaching a regional final for the first time in program history. The Cardinals are the last Valley team still alive and the Valley's first regional finalist since Brownsville Veterans in 2023; coach Joseph Garcia called it 'Ironman Football.'",
 "Small school, players going both ways, and the last team standing in the whole Valley. Coach called it in August.",
 "La Villa is the last Valley team standing, and it's headed to its first regional final ever",5,teaser="La Villa's history-making win",
 confirm="Score also on MaxPreps (42-34) and ValleyCentral; check next week's opponent, date and site before air"),
H("Vela's season ends in regional semifinals, fall to Westlake; PSJA North falls to Dripping Springs 44-27","Vela, PSJA North seasons end in round 3","https://rgvsports.com/velas-season-ends-in-regional-semifinals-fall-to-westlake/","RGVSports \u00b7 Nov 27","2026-11-27T18:23:00-06:00",
 "Edinburg Vela's season ended with a 65-7 loss to Austin Westlake at Heroes Stadium; the SaberCats finish 11-2 with an undefeated 31-6A title in coach Sean Landez's first season. PSJA North fell 44-27 to Dripping Springs at Alamo Stadium, finishing 10-3, its sixth straight 10-win season; coach Marcus Kaufmann said 'Valley football has arrived.'",
 "Two great seasons. Eleven wins and ten wins, and a coach saying the Valley belongs. Tip of the cap.",
 "Vela goes 11-2 and PSJA North gets its sixth straight 10-win season, but both runs end in San Antonio",3,
 teaser="how Vela and PSJA North finished",noprint=False),
H("M\u00e9xico buscar\u00e1 reunirse con EEUU para delimitar el uso que SpaceX le da a su espacio a\u00e9reo (Mexico seeks US talks about suspected SpaceX debris)","Mexico wants US talks on SpaceX launches",AP_ES,"AP / Al Jazeera \u00b7 Nov 26-27","2026-11-26",
 "President Claudia Sheinbaum said Mexico will seek a meeting between U.S. and Mexican airspace authorities to set permission and frequency for SpaceX's use of Mexican airspace and, 'if necessary,' relocation of the launch zone, after debris officials tied to a Nov. 13 Starship flight washed up on Playa Bagdad in Tamaulipas. SpaceX says the small amount found is not clearly from its operations.",
 "Our neighbors across the river want a say in how often Starship flies over them. The 400-launch talk is why.",
 "Mexico wants U.S. talks on how often Starship can use its airspace, and floats moving the launch site",4,theme="RGV Tech",teaser="Mexico vs. Starbase airspace",
 confirm="Follow-up to Nov 24 debris story. Relocation is Sheinbaum's 'if necessary' option, not a formal request (El Economista); RGV.me post drew 131 reactions"),
H("SpaceX Reports Major Cleanup and Conservation Efforts at Boca Chica Beach","SpaceX: 50+ tons of trash off Boca Chica","https://texasborderbusiness.com/spacex-reports-major-cleanup-and-conservation-efforts-at-boca-chica-beach/","Texas Border Business \u00b7 Nov 27","2026-11-27T11:00:00-06:00",
 "SpaceX says it has removed more than 50 tons of trash from Boca Chica Beach and is proposing additional investments to address coastal erosion, protect wildlife and maintain public access to the shoreline, Texas Border Business reports. It comes days after Cameron County passed a resolution protecting public beach access amid SpaceX's bid for state land around Starbase.",
 "Fifty tons is a lot of trash. Also a pretty good week to be talking about it.",
 "SpaceX says it hauled more than 50 tons of trash off Boca Chica Beach",3,theme="RGV Tech",
 confirm="Company's own figures via a Texas Border Business series (only the summary was readable); pair with the county resolution"),
H("La Plaza Mall celebrates 50th Black Friday with giveaways and doorbuster deals","La Plaza's 50th Black Friday: lines at 5 a.m.",VC+"community/la-plaza-mall-celebrates-50th-black-friday-with-giveaways-and-doorbuster-deals/","ValleyCentral \u00b7 Nov 27","2026-11-27T18:19:00-06:00",
 "La Plaza Mall in McAllen marked its 50th year of operation with Black Friday giveaways and special offers; lines were out the door as early as 5 a.m. and as many as half of the mall's retailers offered doorbusters, ValleyCentral reported. KRGV said police in McAllen and Mercedes added patrols at the mall and outlets and urged shoppers to lock cars and keep valuables out of sight.",
 "Fifty years of La Plaza. Half the Valley had its first job or first date there. Who was in line at 5?",
 "La Plaza Mall turns 50 with a 5 a.m. Black Friday line out the door",4,teaser="La Plaza's 50th Black Friday",
 confirm="ValleyCentral feed summary (site blocks our reader); police detail from KRGV"),
H("South Pole Illuminated Festival opens in McAllen with free admission","South Pole Illuminated opens; tree lighting Dec. 2",K+"south-pole-illuminated-festival-opens-in-mcallen-with-free-admission","KRGV \u00b7 Nov 27","2026-11-27",
 "McAllen's South Pole Illuminated Festival, presented by H-E-B with the theme 'Wild Bright,' opened Friday at the McAllen Convention Center with free admission. The South Pole Digital Tree Lighting is Wednesday, Dec. 2, free before 6 p.m.; regular tickets are $12 adults and $7 kids under 12 on weekdays, $15 and $10 on weekends.",
 "Free night one, and a digital tree. McAllen does Christmas like it's a sport.",
 "McAllen's South Pole festival is open, and the digital tree lights up Dec. 2",4,teaser="South Pole Illuminated"),
H("Unlike Corpus, Valley projected to have unmet water needs by 2080","Valley short 591K acre-feet by 2080","https://myrgv.com/local-news/2026/11/27/unlike-corpus-valley-projected-to-have-unmet-water-needs-by-2080/","MyRGV \u00b7 Nov 27","2026-11-27T14:13:00-06:00",
 "State water planning data show the Valley (Region M) needs about 947,000 acre-feet more water than it has in 2030, and even after planned projects it would still be short about 591,000 acre-feet a year in 2080, MyRGV reports. Corpus Christi's region, despite its current crisis, projects no unmet needs after its strategies, thanks to a more diversified supply.",
 "Corpus is the town everyone says is running dry, and on paper we're in worse shape. That's a wake-up call.",
 "Big one: on paper, the Valley's water future looks worse than Corpus Christi's",3,noprint=True),
H("New ag commissioner warns of new pest, shares plans for Valley farmers","Ag Commissioner-elect Tucker on Valley farms","https://myrgv.com/local-news/2026/11/27/new-ag-commissioner-warns-of-new-pest-shares-plans-for-valley-farmers/","MyRGV \u00b7 Nov 27","2026-11-27T14:09:00-06:00",
 "Texas Agriculture Commissioner-elect Clayton Tucker, 35, who takes office Jan. 1 as the first Democrat in the job in nearly 40 years, told MyRGV he is focused on water scarcity, New World screwworm and another invasive pest. He carried all four Valley counties, including Hidalgo 138,511 to 54,581, and warned that after the Santa Rosa sugar mill closure, Texas citrus and rice could be next.",
 "No more Texas sugar, and he's worried citrus is next. That's our grapefruit he's talking about.",
 "The new ag commissioner says the Valley's citrus could follow its sugar mill if water doesn't change",3,noprint=True),
H("Bayview beef ranch fights state's fever tick response protocol","Bayview ranch fights fever tick shots","https://myrgv.com/local-news/2026/11/27/bayview-beef-ranch-fights-states-fever-tick-response-protocol/","MyRGV \u00b7 Nov 27","2026-11-27T13:36:00-06:00",
 "Circle S Beef in Bayview, which markets 'injection-free' beef, self-reported fever ticks in April and is now under a Texas Animal Health Commission quarantine requiring Dectomax injections every 21 to 28 days for at least nine months. The family says injected cattle can no longer be sold under its label and it will stop beef sales if necessary.",
 "Do the right thing, report the ticks, and now the cure kills your brand. Rough spot.",
 "A Bayview ranch reported its own fever ticks; now the required shots could end its injection-free beef",3,noprint=True,
 confirm="Also the Monitor's top readable Facebook post this morning"),
H("McAllen Christmas tree lot receives loyal customers as holiday season begins","McAllen tree lot's loyal customers return",VC+"news/local-news/mcallen-christmas-tree-lot-receives-loyal-customers-as-holiday-season-begins/","ValleyCentral \u00b7 Nov 27","2026-11-27T18:26:00-06:00",
 "As the holiday season opens, Jim and Alicia Connor's McAllen Christmas tree lot is drawing returning customers for real trees the couple handpicked, ValleyCentral reports.",
 "Real tree or fake tree, Jess? This is how fights start in a Valley household.",
 "Real-tree season is open in McAllen, and the regulars are already back",3,noprint=True,
 confirm="ValleyCentral feed summary only (site blocks our reader)"),
H("San Juan police investigating deadly auto-pedestrian crash","San Juan pedestrian, 62, killed",K+"san-juan-police-investigating-deadly-auto-pedestrian-crash","KRGV \u00b7 Nov 27","2026-11-27",
 "A 62-year-old man died after being struck by a driver on Cesar Chavez Road south of Carrol Road at about 6:12 a.m. Friday, San Juan Police Chief Leandro Sifuentes Jr. said. The driver stayed at the scene and is cooperating with police.",
 "Dark mornings this time of year. Slow down and look twice.",
 "Developing: a 62-year-old pedestrian was killed early Friday in San Juan; the driver stayed",1,noprint=True),
H("Two women, gang member linked to severe beating in Cameron County","3 arrested in Cameron Co. beating",VC+"news/local-news/two-women-gang-member-linked-to-severe-beating-in-cameron-county/","ValleyCentral \u00b7 Nov 27","2026-11-27T18:23:00-06:00",
 "The Cameron County Sheriff's Office arrested three people after a 30-year-old woman was found severely beaten early Friday, about 5:23 a.m., ValleyCentral reports.",
 "Three arrests already. Hoping she recovers.",
 "Developing: three arrested after a woman was severely beaten in Cameron County",1,noprint=True,
 confirm="ValleyCentral feed summary only; do not name suspects on air until charges are confirmed"),
]
tx=[
H("Arch Manning and No. 5 Texas grind past Texas A&M 16-6 to secure SEC title game spot","Texas 16, A&M 6: Longhorns to SEC title game","https://www.espn.com/college-football/game/_/gameId/401856756","ESPN (AP) \u00b7 Nov 27","2026-11-27",
 "No. 5 Texas beat Texas A&M 16-6 at Kyle Field on Friday night to clinch a spot in the SEC championship game, ESPN's AP recap says. Coach Steve Sarkisian said he made sure his team was focused only on the Aggies, not what comes next.",
 "Sixteen to six. Not pretty, don't care. Somebody at your Thanksgiving table is still mad.",
 "Texas wins the Lone Star rivalry 16-6 in College Station and punches its ticket to the SEC title game",5,valley=False,teaser="the Longhorns-Aggies result",
 confirm="Score from ESPN scoreboard; only the recap headline and lead were read"),
H("New Democratic attorneys general may reshape justice system","Dem AGs flip 5 states, including Texas",
 "https://www.npr.org/2026/11/28/g-s1-155837/democratic-attorneys-general-justice-system-texas","NPR \u00b7 Nov 28","2026-11-28T04:00:00-06:00",
 "Democrats flipped attorney general offices in Georgia, Iowa, Kansas, Ohio and Texas, where Nathan Johnson was elected, so a majority of states will soon have a Democratic top law enforcement officer, NPR reports. About seven in ten Americans will live in a state with a Democratic AG, which could change which cases get investigated and which lawsuits get filed.",
 "Texas used to be the state suing Washington every week. That job description just changed.",
 "Texas' next attorney general is a Democrat, and NPR says that could reshape which lawsuits get filed",3,valley=False,noprint=True),
H("Spurs ride second-half surge to earn spot in NBA Cup knockout round with 99-96 victory over Lakers","Spurs 99, Lakers 96: into NBA Cup knockouts","https://www.espn.com/nba/game/_/gameId/401909333","ESPN (AP) \u00b7 Nov 27","2026-11-27",
 "Stephon Castle scored 26 and Victor Wembanyama had 25 points and 16 rebounds as San Antonio rallied in the second half to beat the Lakers 99-96 and advance to the NBA Cup knockout round, ESPN's AP recap says. In Phoenix, Cooper Flagg scored 34 as Dallas beat the Suns 113-109 to finish 4-0 in Cup group play.",
 "Wemby and Castle took out the best record in the West. And Flagg went 4-0. Texas basketball's fun again.",
 "The Spurs came back on the Lakers 99-96 and they're into the NBA Cup knockouts",5,valley=False,noprint=True,teaser="Spurs knock out the Lakers"),
H("Texas lawmakers should promote fatherhood, family skills in 2027, report says","Report: Texas should push fatherhood, two-parent homes",
 K+"texas-lawmakers-should-promote-fatherhood-family-skills-in-2027-report-says","Texas Tribune via KRGV \u00b7 Nov 27","2026-11-27T10:34:00-06:00",
 "The Texas Commission on Marriage and Family recommends incentives for two-parent households and fatherhood, a Governor's Office for Families and a fatherhood commission, Texas Tribune reports. With Democrats now controlling the Texas House, the proposals face an uphill battle in the 2027 session.",
 "A state commission wants to teach parenting. Jess, do we get a certificate after 14 years?",
 "A state commission wants Texas to promote fatherhood; the new Legislature may not agree",2,valley=False,noprint=True),
]
d['headlines']={'rgv':rgv,'texas':tx,'image':{"file":"assets/starship_thumb.jpg","caption":"File photo: Starship (Steve Jurvetson, CC BY 2.0, Wikimedia Commons)","credit_url":"https://commons.wikimedia.org/wiki/File:SpaceX_Starship_before_IFT-5.jpg","forItem":2}}
d['nationalDesk']=[
 {"id":"macys-today","title":"Macy's Thanksgiving Day Parade kicks off after being postponed due to weather for first time ever","print":True,
  "summary":"Nov 28: The 100th Macy's parade steps off today at 8:30 a.m. ET after its first-ever postponement; 28 floats, nine marching bands and new Hello Kitty, Minions and Harry Potter characters, with gusts up to 25 mph, under the 34 mph balloon limit (CBS News).",
  "angle":"(Opinion) A hundred years and it finally got rained out. The balloons fly today, two days late. Still counts.",
  "valley":"Harlingen's Monarch Dance Studio dancers were raising money to stay in New York for the new date (KRGV, Nov 26). Watch for them.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/macys-thanksgiving-day-parade-2026-nyc/"}],
  "teaser":"the parade that finally happens today","pfact":"Macy's 100th goes today after 1st-ever delay.","pangle":"Two days late, still counts.","pvalley":"Harlingen dancers tried to stay.",
  "hook":"Postponed for the first time in 100 years, the Macy's parade finally steps off this morning","energy":4,
  "confirm":"Confirm Harlingen dancers are still performing before air"},
 {"id":"dea-tipline","title":"U.S. opens hotline for tips about cartels, as Mexico calls DEA lapses the \"Fast and Furious of Fentanyl\"","print":True,
  "summary":"Nov 27: Mexico lodged a formal complaint with U.S. Ambassador Ron Johnson over DEA anonymous tip lines in Mexico; Sheinbaum called it interference and cited an AP investigation that the DEA let at least 1.4 million counterfeit fentanyl pills go unseized while tracking a ring (CBS News).",
  "angle":"(Opinion) 'Coordination, not subordination.' That line is going on a T-shirt in Mexico City.",
  "valley":"Border cooperation runs through our bridges. When Washington and Mexico City fight, the Valley feels it first.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/us-opens-hotline-tips-cartels-angering-mexico/"}],
  "teaser":"Mexico's formal complaint over DEA tip lines","pfact":"Mexico files complaint over DEA tip lines.","pangle":"Coordination, not subordination.","pvalley":"Valley feels border friction first.",
  "hook":"Mexico files a formal complaint over DEA cartel tip lines and throws the AP's fentanyl report back at Washington","energy":4,
  "confirm":"Follow-up to Nov 27 X News item; now confirmed by CBS/AP"},
 {"id":"reagan-clip","title":"2 American Airlines jets clip wings on tarmac of Reagan Airport","print":True,
  "summary":"Nov 27: American Flight 638, bound for Dallas, clipped the wing of Flight 2152 a little after 5 p.m. while both taxied for departure at Reagan National; no injuries, both planes went back to the gate for inspection, the FAA and airline said (CBS News).",
  "angle":"(Opinion) Black Friday travel, but make it bumper cars.",
  "valley":"Holiday travelers connecting through DFW: check your flights; the Dallas-bound plane was pulled for inspection.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/american-airlines-jets-clip-wings-reagan-airport/"}],
  "teaser":"the wing-clip at Reagan National","pfact":"2 AA jets clip wings at Reagan; no injuries.","pangle":"Tarmac bumper cars.","pvalley":"One was Dallas-bound.",
  "hook":"Two American jets clipped wings while taxiing at Reagan National; one was headed to Dallas, nobody hurt","energy":3},
 {"id":"storm-restore","title":"Power being slowly restored as heavy Thanksgiving storm eases, but flood risk remains","print":False,
  "summary":"Nov 27: Outages that peaked above 900,000 customers fell to just under 300,000 by Friday night; about 3,700 U.S. flights were delayed and 162 canceled, and coastal flood warnings stretched from New Jersey to Virginia (CBS News, FlightAware, PowerOutage.us).",
  "angle":"(Opinion) Six hundred thousand people got their lights back for the leftovers. Small wins.",
  "valley":"Flying home Sunday from the East Coast? Check that connection early.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/east-coast-thanksgiving-storm-power-outages-cleanup/"}],
  "teaser":"the storm cleanup","pfact":"Outages down from 900K+ to under 300K.","pangle":"Lights back for leftovers.","pvalley":"Check Sunday connections.",
  "hook":"Thanksgiving storm outages fall from 900,000 to under 300,000 as the East dries out","energy":2},
]
def T(i,title,cat,one,ang,url,src,short,teaser,hook,en,pr=False,confirm=""):
    return {"id":i,"title":title,"category":cat,"one_line":one,"suggested_angle":ang,"source_url":url,"source":src,"short":short,"teaser":teaser,"verified":True,"confirm":confirm,"print":pr,"links":[],"hook":hook,"energy":en}
d['trending']=[
 T("doncic-shove","Spurs fan shoves Doncic after wristband toss in Lakers loss","sports",
   "After the Spurs' 99-96 win, Luka Doncic tossed his wristband courtside; when a fan refused it he went back and was pushed by a spectator before security stepped in. Doncic said he tosses one nearly every game (X News summary).",
   "Spurs win, and the postgame is a wristband standoff. San Antonio, behave.",
   "https://x.com/i/trending/2126619536300630456","X News \u00b7 Nov 28","Spurs fan shoves Luka","the Luka wristband shove",
   "Luka tried to give a Spurs fan his wristband and got shoved instead",4,pr=True,confirm="X News summary; check video/AP before air; 'Luka', 'Lakers', 'Spurs' all trending on X"),
 T("tupac-tapes","Netflix releases unearthed 1996 Tupac interview tapes","entertainment",
   "'The Tupac Tapes with Angie Martinez,' four episodes out Nov. 27 on Netflix, airs unheard 1996 interview clips with reactions from Ed Lover, RZA and Charlamagne Tha God; 'Tupac' is trending on X (X News summary).",
   "Thirty years in a box, and Angie Martinez finally hits play. Hip-hop Twitter is not okay.",
   "https://x.com/i/trending/2125794986948006007","X News \u00b7 Nov 28","The Tupac Tapes","the Tupac tapes",
   "Angie Martinez sat on hours of 1996 Tupac tapes for 30 years. They're on Netflix now",4,pr=True,confirm="X News summary; keep the Faith Evans claims off air (she denies them)"),
 T("steelers-broncos","Inspired Steelers move on from Rodgers' exit with cathartic 27-5 win over sloppy Broncos","sports",
   "In their first game since Aaron Rodgers' release, the Steelers beat Denver 27-5 on Black Friday (ESPN/AP).",
   "Twenty-seven to five. Five! That's a baseball score, Denver.",
   "https://www.espn.com/nfl/game/_/gameId/401873083","ESPN (AP) \u00b7 Nov 27","Steelers 27, Broncos 5","the Black Friday blowout",
   "First game without Rodgers, and the Steelers hold Denver to five points",3,pr=True,confirm="Only the recap headline and lead were read"),
 T("dog-show","Rocker the coonhound nabs Best in Show at 2026 National Dog Show","feel-good",
   "Rocker, an American English coonhound, won Best in Show at the National Dog Show televised on Thanksgiving; a Lhasa apso named Kissy took reserve. It's Rocker's 15th Best in Show (CBS News).",
   "A coonhound named Rocker. That's a country song waiting to happen.",
   "https://www.cbsnews.com/news/2026-national-dog-show-winner-rocker-coonhound/","CBS News \u00b7 Nov 26","Rocker wins Best in Show","the coonhound champ",
   "A coonhound named Rocker won Best in Show, his 15th, and the judge loved his feet",3,pr=True),
 T("pallbearers","A funeral home asked for pallbearers for a Georgia Army veteran. Hundreds came to say goodbye.","feel-good",
   "When the VA couldn't find family for 94-year-old Korean War-era veteran John Tabor, a Georgia funeral home invited 'everybody' on Facebook; about 400 people, including Patriot Guard riders, came to Georgia National Cemetery (CBS News).",
   "They asked for six pallbearers and 400 showed up. That's America on the day after Thanksgiving.",
   "https://www.cbsnews.com/news/a-funeral-home-asked-for-pallbearers-for-a-georgia-army-veteran-hundreds-came-to-say-goodbye/","CBS News \u00b7 Nov 27","400 show up for a veteran","the veteran nobody forgot",
   "A 94-year-old veteran had no family at his funeral, so about 400 strangers showed up",4),
 T("flagg-mavs","Cooper Flagg leads Mavericks' rally to beat Suns, finish 4-0 in NBA Cup group play","sports",
   "Cooper Flagg scored 34 and led a late charge as Dallas beat Phoenix 113-109 to go a perfect 4-0 in NBA Cup group play (ESPN/AP).",
   "Thirty-four from the rookie, er, the kid. Dallas got its new star.",
   "https://www.espn.com/nba/game/_/gameId/401909332","ESPN (AP) \u00b7 Nov 27","Flagg 34, Mavs 4-0 in Cup","Cooper Flagg's night",
   "Cooper Flagg drops 34 and the Mavs go a perfect 4-0 in NBA Cup group play",3,confirm="Only the recap headline and lead were read"),
 T("cloud-waterfall","Cloud waterfall frames Christ the Redeemer above Rio","viral",
   "Photographer M\u00e1rcio Amaro's iPhone photos of clouds spilling down Mount Corcovado, leaving only the statue visible above a sea of white, went viral (X News summary).",
   "Shot on an iPhone. My iPhone photos are of my thumb.",
   "https://x.com/i/trending/2126163960202248683","X News \u00b7 Nov 28","Rio's cloud waterfall","the cloud waterfall photo",
   "Clouds poured down a mountain in Rio like a waterfall, and one guy caught it on his iPhone",3,confirm="X News summary; credit the photographer if shown"),
]
d['tech']={"origin":"wires","issue":None,"searchedAt":"2026-11-28T06:20:00-06:00",
 "note":"No Fast Company Daily issue found in the last 48 h: searched Drew's Gmail read-only on Nov 28, 2026 at about 6:20 AM CT (drew@drewlentz.com, then drew@politiquera.com) for (from:fastcompany OR subject:\"Fast Company Daily\") newer_than:2d. RGV tech items come first from local outlets; national items are the fallback from the tech wires (The Verge, TechCrunch, Ars Technica) plus CBS News.",
 "items":[
  {"id":"mx-spacex-talks","title":"Mexico seeks US talks about suspected SpaceX debris","short":"Mexico wants SpaceX airspace talks","source":"AP / Al Jazeera","source_url":AJ,"published":"Nov 26-27",
   "one_line":"Sheinbaum wants U.S.-Mexico airspace talks on how often SpaceX can use Mexican airspace and, if necessary, relocating the launch zone, after suspected Starship debris washed up on Playa Bagdad.",
   "angle":"Starbase's growth plans now have a foreign-policy question attached.","hook":"Mexico wants a say in how often Starship flies, and floats moving the launch site","energy":4,"verified":True,"confirm":"SpaceX disputes the debris is clearly its own","links":[{"label":"AP (Spanish)","url":AP_ES}],"basis":"AP / Al Jazeera \u00b7 RGV Tech","valley":True},
  {"id":"boca-cleanup","title":"SpaceX Reports Major Cleanup and Conservation Efforts at Boca Chica Beach","short":"SpaceX: 50 tons of beach trash","source":"Texas Border Business","source_url":"https://texasborderbusiness.com/spacex-reports-major-cleanup-and-conservation-efforts-at-boca-chica-beach/","published":"Nov 27",
   "one_line":"SpaceX says it removed more than 50 tons of trash from Boca Chica Beach and proposes more spending on erosion, wildlife and public access.",
   "angle":"The PR push lands the same week as the county's public-access resolution.","hook":"SpaceX says it hauled more than 50 tons of trash off Boca Chica Beach","energy":3,"verified":True,"confirm":"Company figures","links":[],"basis":"Texas Border Business \u00b7 RGV Tech","valley":True},
  {"id":"af-cloud-breach","title":"U.S. Air Force cloud platform breached by hackers, report says","short":"Air Force Cloud One breached","source":"CBS News (Reuters)","source_url":"https://www.cbsnews.com/news/u-s-air-force-cloud-platform-breached-by-hackers/","published":"Nov 27",
   "one_line":"Hackers breached Cloud One, the Air Force's flagship cloud platform, possibly exposing military and personnel data, sources told Reuters; the Air Force would not confirm or deny.",
   "angle":"If the Air Force's cloud can get popped, change that reused password tonight.","hook":"Hackers reportedly got into the Air Force's main cloud platform","energy":3,"verified":True,"confirm":"Sourced reporting; not confirmed by the Air Force","links":[]},
  {"id":"openai-apple","title":"OpenAI countersues Apple over allegations of stealing trade secrets","short":"OpenAI countersues Apple","source":"CBS News","source_url":"https://www.cbsnews.com/news/openai-countersues-apple-trade-secrets-lawsuit/","published":"Nov 27",
   "one_line":"Answering Apple's June trade-secrets suit, OpenAI alleges Apple sets up departing employees to be accused of stealing; Apple calls the counterclaims a distraction.",
   "angle":"The two companies behind the phone in your pocket and the chatbot on it are now suing each other.","hook":"OpenAI fires back at Apple: you set up your ex-employees","energy":3,"verified":True,"confirm":"","links":[]},
  {"id":"intel-10","title":"Intel faced a choice: Give Trump 10% or face the consequences","short":"Intel and the 10% stake","source":"Ars Technica","source_url":"https://arstechnica.com/tech-policy/2026/11/intel-faced-a-choice-give-trump-10-or-face-the-consequences/","published":"Nov 27",
   "one_line":"Ars reports Intel faced pressure to surrender a 10% stake to unlock billions in promised grants.",
   "angle":"Chips money with strings attached, a big deal for every place chasing a fab or data center.","hook":"Intel was pressured to hand over 10% to unlock its chip grants, Ars reports","energy":3,"verified":True,"confirm":"Only the headline and deck were read","links":[]},
 ]}
s=d['sports']
s['highSchool']['round']="Regional finals next: La Villa (12-1) is the last Valley team alive after beating Falls City 42-34 in the Region IV-2A DII semifinals. Vela (11-2) and PSJA North (10-3) were eliminated Friday."
s['highSchool']['sourceNote']="RGVSports game stories (Nov 27), MaxPreps box score. La Villa's regional-final opponent, date and site were not posted at 6:30 AM CT; check RGVSports before air."
s['highSchool']['results']=[
 {"title":"La Villa 42, Falls City 34 (Region IV-2A DII semifinal, Alice): first regional final in program history","short":"La Villa 42, Falls City 34","url":"https://rgvsports.com/marching-on-la-villa-holds-off-falls-city-advances-to-regional-final/","source":"RGVSports \u00b7 Nov 27"},
 {"title":"Dripping Springs 44, PSJA North 27 (Region IV-6A semifinal, Alamo Stadium): Raiders finish 10-3","short":"Dripping Springs 44, PSJA North 27","url":"https://rgvsports.com/down-swinging-raiders-fall-short-against-tigers/","source":"RGVSports \u00b7 Nov 27"},
 {"title":"Austin Westlake 65, Edinburg Vela 7 (Region IV-6A DII semifinal, Heroes Stadium): SaberCats finish 11-2","short":"Westlake 65, Vela 7","url":"https://rgvsports.com/velas-season-ends-in-regional-semifinals-fall-to-westlake/","source":"RGVSports \u00b7 Nov 27"}]
s['highSchool']['next']=[
 {"title":"La Villa vs. TBD, Region IV-2A DII final (date/site TBA)","short":"La Villa in regional final, TBA","url":"https://www.rgvsports.com/rgv-football-playoff-schedule/","source":"RGVSports","confirm":"Opponent, date and site not yet posted"}]
s['nfl']={"title":"NFL Black Friday: Steelers 27, Broncos 5","scoreSource":{"title":"ESPN NFL scoreboard, Fri Nov 27","short":"","url":"https://www.espn.com/nfl/scoreboard/_/week/12/year/2026/seasontype/2","source":"ESPN"},
 "scores":[["Fri Nov 27","PIT 27, DEN 5"],["Thu Nov 26","CHI 39, DET 35"],["Thu Nov 26","PHI 39, DAL 38"],["Thu Nov 26","BUF 13, KC 10"]],
 "notable":[{"title":"Inspired Steelers move on from Rodgers' exit with cathartic 27-5 win over sloppy Broncos","short":"Steelers' first game post-Rodgers","url":"https://www.espn.com/nfl/game/_/gameId/401873083","source":"ESPN (AP) \u00b7 Nov 27"}]}
n=s['nba']
n['scoreSource']={"title":"ESPN NBA scoreboard, Fri Nov 27 (NBA Cup)","short":"","url":"https://www.espn.com/nba/scoreboard/_/date/20261127","source":"ESPN"}
n['scores']=[["Fri Nov 27","SA 99, LAL 96"],["Fri Nov 27","DAL 113, PHX 109"],["Fri Nov 27","MIA 108, NY 105"],["Fri Nov 27","ATL 87, BOS 86"],["Fri Nov 27","DEN 120, UTAH 107"],["Fri Nov 27","NO 105, LAC 104"]]
n['texas']=[["Fri Nov 27","SA 99, LAL 96"],["Fri Nov 27","DAL 113, PHX 109"]]
s['highSchool']['college']={"title":"No. 5 Texas 16, Texas A&M 6 at Kyle Field; Longhorns clinch SEC title game spot","short":"Texas 16, A&M 6 (Fri)","url":"https://www.espn.com/college-football/game/_/gameId/401856756","source":"ESPN (AP) \u00b7 Nov 27"}
d['leads']=[]
d['chisme']={}
o=json.load(open('/tmp/obits.json')); d['obituaries']=o
for k in ['up_to','up_to_script','up_to_meta','up_to_coming']: d.pop(k,None)
json.dump(d,open(P+'packet-2026-11-28.json','w'),indent=1,ensure_ascii=False)
print('ok',len(rgv),len(tx))
