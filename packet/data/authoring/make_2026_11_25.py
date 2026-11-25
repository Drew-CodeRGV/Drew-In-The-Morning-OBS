import json
P='/workspace/drew-in-the-morning/packet/data/'
d=json.load(open(P+'packet-2026-11-24.json'))
d['meta'].update({"date":"2026-11-25","title":"Drew in the Morning \u00b7 Daily Briefing","dataAsOf":"Nov 25, 2026, 6:45 AM CT",
 "recap":"Last 24 hours (Nov 24-25), story bank for Monday Nov 30","mode":"daily","showDate":"2026-11-30","sample":False,
 "dateLabel":"Wednesday, November 25, 2026",
 "kidsTopic":"AI toys on the holiday list: CBS News (Nov 24) reports a U.S. PIRG test of seven AI toys found some had glitchy guardrails that let them discuss sexual topics or explain where knives are and how to light a match. Ask the 10-year-old whether a talking toy is a friend or a computer; ask the 14-year-old what rules they'd set for an AI chatbot their little sibling uses"})
def H(title,short,url,source,pub,tldr,riff,hook,energy,valley=True,confirm=None,teaser=None,noprint=False):
    it={"title":title,"short":short,"url":url,"source":source,"published":pub,"valley":valley,"tldr":tldr,"riff":riff,"hook":hook,"energy":energy,"links":[]}
    if confirm: it["confirm"]=confirm
    if teaser: it["teaser"]=teaser
    if noprint: it["noprint"]=True
    return it
VCN="ValleyCentral blocks our reader; TL;DR from the ValleyCentral feed summary"
rgv=[
H("Made in the 956: Weslaco native Chuck Leah earns Grammy nomination","Weslaco's Chuck Leah: Grammy nominee",
 "https://www.krgv.com/news/made-in-the-956-weslaco-native-chuck-leah-earns-grammy-nomination","KRGV \u00b7 Nov 24","2026-11-24T15:12:00-06:00",
 "Weslaco native Chuck Leah was nominated for Best American Roots Performance for his song \u201cCoyote,\u201d putting him alongside artists including Sara Bareilles and Brandi Carlile. He lives in Houston and says he started recording as a kid at Master Productions in Weslaco, and that Valley folk, Mexican folk and country music are in his \u201crecipe.\u201d",
 "From a Weslaco recording studio to the Grammys. The Valley sound just got a national stage.",
 "A Weslaco kid who started recording at Master Productions is now a Grammy nominee",5,teaser="Weslaco's Grammy nominee"),
H("Officers may swap traffic tickets for turkeys in McAllen","McAllen PD: ticket or turkey today",
 "https://www.valleycentral.com/news/local-news/officers-may-swap-traffic-tickets-for-turkeys-in-mcallen/","ValleyCentral \u00b7 Nov 24","2026-11-24T16:57:00-06:00",
 "McAllen police officers may hand drivers a Thanksgiving turkey instead of a traffic ticket on Wednesday morning. The department is taking part in \u201cTicket or Turkey,\u201d a goodwill gesture for the season, and Sgt. John Saenz said officers will use their discretion.",
 "Getting pulled over and driving away with a turkey. Still, use your blinker.",
 "Pulled over in McAllen this morning? You might drive off with a turkey instead of a ticket",5,confirm=VCN,teaser="ticket or turkey in McAllen"),
H("First case of New World screwworm confirmed in Cameron County; RGV total rises to 11","Screwworm hits Cameron County; RGV at 11",
 "https://www.krgv.com/news/first-case-of-new-world-screwworm-confirmed-in-cameron-county-rgv-total-rises-to-11","KRGV \u00b7 Nov 24","2026-11-24T18:04:00-06:00",
 "The USDA confirmed Cameron County's first case of New World screwworm on Tuesday, the same day state officials confirmed two more cases in Hidalgo County, bringing that county to three. With seven active cases in Starr County, the Valley-wide total is 11. Hidalgo County Judge Richard F. Cortez urged livestock and pet owners to watch for signs and report suspected cases.",
 "It's in all three big counties now. If you have animals, look twice and call it in.",
 "Big one: screwworm reaches Cameron County, and the Valley total climbs to 11",4,teaser="screwworm in Cameron County"),
H("NFL Star Von Miller Receives Warm Welcome in McAllen Ahead of Holiday Parade","Von Miller + McAllen parade Dec 5",
 "https://texasborderbusiness.com/nfl-star-von-miller-receives-warm-welcome-in-mcallen-ahead-of-holiday-parade/","Texas Border Business \u00b7 Nov 24","2026-11-24T11:49:00-06:00",
 "NFL star Von Miller got an enthusiastic welcome at McAllen International Airport on Nov. 17, meeting fans and talking about his charitable work and the McAllen Holiday Parade. The 2026 parade, themed Wild Christmas, is Saturday, Dec. 5, at 6 p.m., starting at McAllen Veterans Memorial Stadium and running along Bicentennial Boulevard; gates open at 3:30 p.m.",
 "A Super Bowl MVP and a Wild Christmas theme. McAllen does parades right.",
 "Von Miller in McAllen, and the Wild Christmas parade rolls Dec. 5",4,confirm="Article dated Nov 24 describes a Nov 17 airport visit; confirm Miller's parade role before air"),
H("'Plebe-giving': El Plebe giving out free tacos ahead of Thanksgiving","El Plebe 'Plebe-giving' free tacos",
 "https://www.valleycentral.com/news/local-news/plebe-giving-el-plebe-giving-out-free-tacos-ahead-of-thanksgiving/","ValleyCentral \u00b7 Nov 24","2026-11-24T19:33:00-06:00",
 "Tacos El Plebe is partnering with the Food Bank of the Rio Grande Valley for its first holiday event, \u201cPlebe-giving,\u201d serving its newest menu item, the puercaso taco, while giving back to the community.",
 "Free tacos and a food bank assist. Plebe-giving might be the Valley's best new holiday.",
 "Free tacos for a good cause: El Plebe's first-ever Plebe-giving with the Food Bank RGV",5,confirm=VCN+"; time, location and giveaway details not read; CONFIRM BEFORE AIR",teaser="Plebe-giving tacos"),
H("Rio Grande Valley DA Coalition launches holiday 'No Refusal' DWI initiative","No Refusal starts today, to Jan 3",
 "https://www.krgv.com/news/rio-grande-valley-da-coalition-launches-holiday-no-refusal-dwi-initiative","KRGV \u00b7 Nov 24","2026-11-24T20:02:00-06:00",
 "District attorneys in Cameron, Hidalgo, Willacy and Starr counties launched the holiday \u201cNo Refusal\u201d DWI initiative, running Wednesday, Nov. 25, 2026, through Sunday, Jan. 3, 2027. Officers can seek expedited search warrants for blood samples from drivers who refuse a breath test.",
 "Translation: refuse the breathalyzer, they get a warrant. Plan the ride before the first drink.",
 "No Refusal starts today in all four Valley counties: refuse the breath test, expect a warrant",3),
H("Sharyland ISD students fulfill 500 wish lists through Angel Tree program","Pioneer HS: 500 Angel Tree wishes",
 "https://www.krgv.com/news/sharyland-isd-students-fulfill-500-wish-lists-through-angel-tree-program","KRGV \u00b7 Nov 24","2026-11-24T12:31:00-06:00",
 "Eighty Pioneer High School students shopped through the Salvation Army's Angel Tree program so 500 children will have Christmas presents to open. The effort is a partnership between Sharyland ISD and the Salvation Army; one student told KRGV she was once an Angel Tree child herself.",
 "80 teenagers, 500 wish lists. Teens get a bad rap; this is the other side.",
 "80 Pioneer High students shopped so 500 kids get Christmas presents",4),
H("Solis: AI will not replace workers, but workers who know how to use AI will","STC's Solis: learn AI or get passed",
 "https://riograndeguardian.com/stories/solis-ai-will-not-replace-workers-but-workers-who-know-how-to-use-ai-will,91689","Rio Grande Guardian \u00b7 Nov 24","2026-11-24T17:11:00-06:00",
 "At STC's Annual Workforce Summit, President Ricardo Solis said the Valley faces a \u201cskills challenge,\u201d not just a worker shortage, driven by AI and industrial growth: people who know how to use AI will replace those who don't. He said STC enrollment tops 42,000 and the college is ramping up welding, electronics, precision manufacturing and mechatronics for port and Boca Chica jobs.",
 "AI won't take your job; the coworker who knows AI might. Good line for every Valley parent.",
 "STC's president: AI won't replace you, but people who know AI will",4,teaser="STC's AI warning"),
H("Elon Musk\u2019s SpaceX Data Centers Face Key Votes on Same Day in December","Starbase data center vote: Dec 9",
 "https://www.newsweek.com/elon-musks-spacex-data-centers-face-key-votes-on-same-day-in-december-12764916","Newsweek \u00b7 Nov 24","2026-11-24T19:33:00-06:00",
 "On Dec. 9 the Starbase City Commission is scheduled to consider a 10-year, 100% property tax abatement for SpaceX's $24 billion, 444-acre data center near Brownsville, the same day an Arizona county votes on a $50 billion SpaceX campus. SpaceX says the Texas project has created more than 3,000 construction jobs, with 500-plus permanent jobs coming, and pledged $200 million for Brownsville water and wastewater.",
 "County said no, so the ask moves to a city where two of three commissioners work for SpaceX. Dec. 9 is the date to watch.",
 "After Cameron County said no, SpaceX's $24 billion data center tax break goes to Starbase on Dec. 9",4,teaser="SpaceX's Dec. 9 data center vote"),
H("Harlingen to add crosswalks, ramps on South M Street to improve safety","Harlingen: M Street crosswalks",
 "https://www.krgv.com/news/harlingen-to-add-crosswalks-ramps-on-south-m-street-to-improve-safety","KRGV \u00b7 Nov 25","2026-11-25T04:18:00-06:00",
 "Harlingen plans marked crosswalks and accessible ramps on South M Street between Hanson and Hays avenues, with work that could begin in four to six weeks. A lifelong resident told KRGV the stretch near homes and a school has needed safer crossings for a long time.",
 "Neighbors asked, the city answered. Four to six weeks. We'll check.",
 "Harlingen answers M Street neighbors: crosswalks and ramps could start in four to six weeks",3),
H("Mission EDC Awards Business Grants to 16 Local Entrepreneurs","Mission EDC: grants to 16 businesses",
 "https://texasborderbusiness.com/mission-edc-awards-business-grants-to-16-local-entrepreneurs/","Texas Border Business \u00b7 Nov 24","2026-11-24T09:07:00-06:00",
 "The Mission Economic Development Corporation recognized 16 local businesses on Nov. 20 in the fourth cycle of its Ruby Red Ventures \u2013 Build Mission Fund, supporting investments in equipment, technology, facility improvements and expansion. Recipients ranged from manufacturing and technology to retail, healthcare and professional services.",
 "Sixteen small businesses getting a boost. That's the EDC money people actually see.",
 "16 Mission small businesses win Ruby Red Ventures grants",3),
H("Weslaco EDC Honors Jerry Gonzalez for Six Years of Leadership Behind $234M in Economic Investment","Weslaco EDC: 1,722 jobs, $234M",
 "https://texasborderbusiness.com/weslaco-edc-honors-jerry-gonzalez-for-six-years-of-leadership-behind-234m-in-economic-investment/","Texas Border Business \u00b7 Nov 24","2026-11-24T10:10:00-06:00",
 "Over six years the Economic Development Corporation of Weslaco supported 110 projects, helped create 1,722 jobs and contributed to $234,647,852 in capital investment. The EDC is honoring longtime banker Jerry Gonzalez for six years as board president, vice president, treasurer and director.",
 "1,722 jobs in six years. Weslaco's quietly putting up numbers.",
 "Weslaco EDC by the numbers: 110 projects, 1,722 jobs, $234 million",3,noprint=True),
H("Elsa proposes turning gravel pits into flood retention ponds","Elsa: gravel pits to flood ponds",
 "https://www.krgv.com/news/elsa-proposes-turning-gravel-pits-into-flood-retention-ponds","KRGV \u00b7 Nov 24","2026-11-24T07:47:00-06:00",
 "Elsa officials are studying a plan to convert two gravel pits into retention ponds to hold excess rainwater and reduce flooding in Elsa, Edcouch and La Villa. The Texas Water Development Board will put $223,000 toward the study; the project is exploratory for now.",
 "Old holes in the ground as flood insurance. That's smart, cheap thinking.",
 "Elsa's idea: turn two gravel pits into flood ponds, with $223,000 from the state to study it",3,noprint=True),
H("Brownsville residents push back against proposed duplexes over flooding, traffic concerns","Brownsville duplex fight, Dec 1 vote",
 "https://www.krgv.com/news/brownsville-residents-push-back-against-proposed-duplexes-over-flooding-traffic-concerns","KRGV \u00b7 Nov 24","2026-11-24T23:18:00-06:00",
 "Brownsville residents on Carlton Drive are raising flooding, sewer and traffic concerns ahead of a Dec. 1 vote on a zoning request for four duplexes across two properties. A neighbor since the 1960s said he won't trust it until heavy rain stops flooding the street.",
 "Housing versus drainage: the fight every growing Valley city is having.",
 "Brownsville neighbors vs. four duplexes: flooding fears ahead of a Dec. 1 zoning vote",2,noprint=True),
H("City Hall Prepares for \u2018A Season of Sparkle: A Very Merry Production\u2019, Dec 1 in McAllen","McAllen City Hall tree lighting Dec 1",
 "https://texasborderbusiness.com/city-hall-prepares-for-a-season-of-sparkle-a-very-merry-production-dec-1-in-mcallen/","Texas Border Business \u00b7 Nov 24","2026-11-24T11:25:00-06:00",
 "McAllen will light its first City Hall Christmas tree at \u201cA Season of Sparkle: A Very Merry Production\u201d on Tuesday, Dec. 1, 5 to 6:30 p.m. at City Hall, 1300 W. Houston Ave., with performances by UTRGV and McAllen ISD students and giveaways from Santa.",
 "An inaugural City Hall tree. McAllen, the Christmas capital, adds another light.",
 "McAllen lights its first-ever City Hall Christmas tree Dec. 1",3,noprint=True),
H("Tres Lagos homeowners frustrated after hundreds of dollars in Christmas decorations stolen","Tres Lagos decorations stolen",
 "https://www.krgv.com/news/tres-lagos-homeowners-frustrated-after-hundreds-of-dollars-in-christmas-decorations-stolen","KRGV \u00b7 Nov 24","2026-11-24T22:37:00-06:00",
 "McAllen police are investigating after several residents in the Tres Lagos community said their Christmas decorations were stolen overnight. One homeowner said two inflatables, a Christmas tree and a reindeer, were taken from her yard and her plants were stomped on.",
 "Stealing a reindeer inflatable before Thanksgiving. That's a coal-in-the-stocking crime.",
 "Grinches in Tres Lagos: McAllen police investigate stolen Christmas inflatables",2,noprint=True),
H("Greater Brownsville EDC\u2019s Jerry Briones Named to Team Texas Advisory Council","GBEDC's Briones on Team Texas council",
 "https://texasborderbusiness.com/greater-brownsville-edcs-jerry-briones-named-to-team-texas-advisory-council/","Texas Border Business \u00b7 Nov 24","2026-11-24T11:59:00-06:00",
 "Greater Brownsville EDC Executive Vice President Jerry Briones was appointed to the Team Texas Advisory Council, a statewide group that guides efforts to promote Texas to domestic and international investors.",
 "A Brownsville voice in the room where Texas pitches itself. That matters for the port and Boca Chica.",
 "Brownsville's EDC gets a seat on the statewide Team Texas council",2,noprint=True),
]
tx=[
H("College Football Playoff Rankings: Texas, Notre Dame join top four as Tennessee leaps Alabama","Texas up to No. 3 in CFP rankings",
 "https://www.cbssports.com/college-football/news/college-football-playoff-rankings-top-25-week-13-2026/","CBS Sports \u00b7 Nov 24","2026-11-24T19:42:00-06:00",
 "Texas jumped to No. 3 in the fourth College Football Playoff rankings after UCLA's loss. The Longhorns have won five straight and can clinch an SEC Championship Game spot with a win over Texas A&M plus a loss by Alabama or Tennessee.",
 "Five straight wins and the Aggies on deck. Thanksgiving week just got loud in Texas.",
 "Longhorns crash the top four: No. 3 in the playoff rankings with A&M up next",5,valley=False,teaser="Texas at No. 3"),
H("New ACA identity checks delay health insurance enrollment","ACA ID checks slow TX enrollment",
 "https://www.texastribune.org/2026/11/24/texas-aca-health-insurance-enrollment-costs-delays/","Texas Tribune \u00b7 Nov 24","2026-11-24T14:35:00-06:00",
 "Of the 760,000 Affordable Care Act enrollees removed from the rolls this year, nearly half were in Texas, the Tribune reports. New identity verification methods are now part of open enrollment for 2027 coverage, delaying some sign-ups.",
 "The Valley leans on ACA plans more than most. If you're enrolling, start early.",
 "Nearly half of 760,000 ACA enrollees cut this year were Texans, and new ID checks slow sign-ups",3,valley=False),
H("New cypress trees help heal flood-torn Guadalupe River","Cypress replanting on the Guadalupe",
 "https://www.texastribune.org/2026/11/24/texas-floods-trees-guadalupe-river-recovery-kerr-county/","Texas Tribune \u00b7 Nov 24","2026-11-24T05:00:00-06:00",
 "After deadly floods devastated Kerr County, Texans are planting native cypress trees along the Guadalupe River to restore its ecosystem and help communities recover.",
 "Planting trees is how you say 'we're staying.' A hopeful one for Thanksgiving week.",
 "Hope on the Guadalupe: new cypress trees take root after Kerr County's deadly floods",3,valley=False),
H("Texas\u2019 first study of college DEI ban leaves key questions unanswered","TX DEI-ban report: questions remain",
 "https://www.texastribune.org/2026/11/24/texas-college-dei-ban-student-impact-report/","Texas Tribune \u00b7 Nov 24","2026-11-24T05:00:00-06:00",
 "Texas universities cut many student supports under the state's DEI ban. A new state report shows academic gains but cannot yet measure the law's effect on graduation, the Tribune reports.",
 "UTRGV students live this. The data isn't in yet on graduation.",
 "Texas' first look at the college DEI ban: academic gains, but no answer yet on graduation",2,valley=False),
]
d['headlines']['rgv']=rgv; d['headlines']['texas']=tx
d['headlines'].pop('image',None)
d['nationalDesk']=[
 {"id":"iowa-detonation","title":"Army to detonate unstable lead explosives at Iowa munitions plant despite community concerns","print":True,
  "summary":"Nov 25: The Army plans to blow up five tons of degraded lead azide at the Iowa Army Ammunition Plant in Middletown at 9 a.m. local time after a legal fight delayed it; Army maps say the dust could travel up to 100 miles, with the strongest effects within 30 square miles.",
  "angle":"(Opinion) Blow it up on purpose or wait for it to blow up on its own. Nobody in Middletown is getting a good night's sleep.",
  "valley":"The Valley has its own explosion debate: Starbase. Same question every time: who gets told what, and when.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/iowa-army-ammunition-plant-unstable-explosives-detonation/"},{"label":"The Verge","url":"https://www.theverge.com/science/1041819/us-army-detonation-lead-explosives-iowa"}],
  "teaser":"the Army's 5-ton Iowa blast","pfact":"Army blows up 5 tons of lead azide in Iowa today.","pangle":"Dust could travel 100 miles.","pvalley":"Starbase knows this debate.",
  "hook":"Five tons of unstable explosives, one controlled blast in Iowa this morning","energy":4},
 {"id":"trump-nvidia-stock","title":"Trump owned millions in Nvidia stock as he pressed chip giant to reinstate Jensen Huang","print":True,
  "summary":"Nov 25: Financial disclosures show President Trump held $13 million to $58 million in Nvidia stock at the end of 2025; he said he 'convinced' Nvidia's board to rehire Huang, and the stock surged more than 30% on Huang's return Monday.",
  "angle":"(Opinion) When the guy who made the call also owns the stock, people are going to ask questions. CBS says his stake rose $1.3M to $14.8M in a day.",
  "valley":"Nvidia chips are what power the data centers being pitched to the Valley, including SpaceX's Starbase project.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/trump-nvidia-stock-jensen-huang/"}],
  "teaser":"Trump's Nvidia shares","pfact":"Trump held $13M-$58M in Nvidia stock.","pangle":"Stock up 30% on Huang's return.","pvalley":"Chips behind Valley data-center pitches.",
  "hook":"Trump pushed Nvidia to rehire Huang, and disclosures show he owns millions in Nvidia stock","energy":3},
 {"id":"abrego-garcia-spain","title":"Kilmar Abrego Garcia leaves U.S., heads to Spain","print":True,
  "summary":"Nov 24: Kilmar Abrego Garcia, mistakenly deported to El Salvador last year, left the U.S. for Spain on a commercial flight, DHS and his team confirmed; a judge's order from Friday remains sealed. He said he leaves 'happy' and 'with his freedom.'",
  "angle":"(Opinion) The face of the deportation fight ends it on a plane to Spain. The terms are sealed, so everybody gets to argue about who won.",
  "valley":"Valley families are living their own versions of this story; the Monitor reports a longtime Valley resident detained by ICE Nov. 10 near San Benito.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/kilmar-abrego-garcia-leaving-us-europe/"},{"label":"NPR","url":"https://www.npr.org/2026/11/25/nx-s1-6053203/abrego-garcia-leaves-us"},{"label":"The Monitor","url":"https://myrgv.com/local-news/2026/11/24/family-seeks-medical-care-for-longtime-valley-resident-detained-by-ice/"}],
  "teaser":"Abrego Garcia's exit to Spain","pfact":"Abrego Garcia leaves U.S. for Spain.","pangle":"Terms sealed.","pvalley":"Valley ICE cases continue.",
  "hook":"The man at the center of the deportation fight leaves the U.S. for Spain, terms sealed","energy":3},
 {"id":"mississippi-plane","title":"Small plane crash off Mississippi kills 6, including 2 children, Coast Guard says","print":False,
  "summary":"Nov 24: Divers found six people dead in the fuselage of a Cessna 210 that went down in the Gulf between Pascagoula and Horn Island; the FAA said it was descending at 10,000 feet per minute when contact was lost.",
  "angle":"(Opinion) A heartbreaking start to a holiday week. Keep it brief and respectful.",
  "valley":"Same Gulf, a few hundred miles east. Holiday travelers, check in with family when you land.",
  "links":[{"label":"CBS News","url":"https://www.cbsnews.com/news/small-plane-crash-off-mississippi-6-dead-2-children/"}],
  "teaser":"the Mississippi plane crash","pfact":"6 die in Gulf plane crash off Mississippi.","pangle":"Respectful, brief.","pvalley":"Same Gulf.",
  "hook":"Developing: six killed when a small plane goes down in the Gulf off Mississippi","energy":1},
]
def T(i,title,cat,one,ang,url,src,short,teaser,hook,en,pr=False,confirm=""):
    return {"id":i,"title":title,"category":cat,"one_line":one,"suggested_angle":ang,"source_url":url,"source":src,"short":short,"teaser":teaser,"verified":True,"confirm":confirm,"print":pr,"links":[],"hook":hook,"energy":en}
d['trending']=[
 T("iss-baby","Wife of Canadian astronaut aboard International Space Station gives birth to couple's third child","feel-good",
   "Nov 24: Heather Kutryk gave birth to a girl while husband Joshua Kutryk is aboard the ISS; the Canadian Space Agency said mom and baby are doing well and he shared in the experience from orbit.",
   "Dad's literally in orbit. 'Our new little star.' Best birth announcement of the year.",
   "https://www.cbsnews.com/news/wife-canadian-astronaut-international-space-station-gives-birth-joshua-kutryk/","CBS News \u00b7 Nov 24","Baby born while dad's on the ISS","the space-station baby",
   "A baby girl is born while her dad watches from the International Space Station",5,True),
 T("one-last-order","Beloved drive-thru worker and star of Netflix film \"on top of the world\" after making a year's salary on last day of work","feel-good",
   "Sighle Williams retired after 37 years at Mac's Drive Thru in Gainesville, Florida; her last day is the subject of the award-winning Netflix short 'One Last Order,' which premiered Tuesday.",
   "37 years of making people smile, and her customers paid it back with a year's salary. Bring tissues.",
   "https://www.cbsnews.com/news/sighle-williams-star-new-netflix-film-one-last-order/","CBS News \u00b7 Nov 24","Drive-thru legend's last day: a year's salary","the drive-thru worker's send-off",
   "37 years at the drive-thru, and her last day earned a year's salary and a Netflix film",5,True),
 T("rodgers-benched","Steelers bench Aaron Rodgers, turn to Mason Rudolph to start vs. Broncos","sports",
   "Nov 24: Pittsburgh (6-4) benched Rodgers after back-to-back losses following a 6-2 start; Mason Rudolph starts Black Friday against Denver. Rodgers turns 43 on Dec. 2.",
   "Black Friday doorbuster: one future Hall of Famer, marked down to backup.",
   "https://www.cbssports.com/nfl/news/steelers-bench-aaron-rodgers-make-qb-inactive-friday-broncos/","CBS Sports \u00b7 Nov 24","Steelers bench Aaron Rodgers","Rodgers to the bench",
   "Is this how it ends? The Steelers bench Aaron Rodgers a week before he turns 43",4,True),
 T("shenzhou-24","China's Shenzhou 24 mission lifts off, carrying first foreign astronaut to its space station","science",
   "Nov 25: China launched Shenzhou 24 with two Chinese astronauts and Pakistan's Muhammad Zeeshan Ali, the first foreign crew member on China's space station; the crew plans more than 90 experiments.",
   "Space is getting crowded: an ISS baby announcement and China's first foreign astronaut in the same 24 hours.",
   "https://www.cbsnews.com/news/china-launches-shenzhou-24-spacecraft/","CBS News \u00b7 Nov 24","China flies its first foreign astronaut","China's first foreign astronaut",
   "China launches its first foreign astronaut, from Pakistan, to its space station",3),
 T("senegal-afcon","Africa Cup title given back to Senegal after sports court rules against Morocco","sports",
   "The Court of Arbitration for Sport overturned a March ruling that had handed the January Africa Cup of Nations title to Morocco after Senegal's players walked off in protest; Senegal is champion again.",
   "Won it on the field, lost it in court, won it back in court. Ten months of 'who's the champ?'",
   "https://www.npr.org/2026/11/25/nx-s1-6053783/africa-cup-senegal-morocco","NPR/AP \u00b7 Nov 25","Senegal gets its Africa Cup title back","the Africa Cup flip-flop",
   "Won on the field, stripped in court, now champions again: Senegal gets the Africa Cup back",3),
 T("royal-burglary","Prince William and Catherine's country home broken into; 2 men arrested","celebrity",
   "Police said two men were charged after a suspected break-in Monday at Anmer Hall on the Sandringham estate; William, Catherine and family were not there. Dogs, drones and a helicopter were used in the search.",
   "Dogs, drones and a helicopter. If you're going to rob a prince, expect the full package.",
   "https://www.cbsnews.com/news/prince-william-kate-country-home-broken-into-british-media/","CBS News \u00b7 Nov 24","Break-in at William and Kate's country home","the royal break-in",
   "Break-in at William and Kate's country home: two men charged, the family wasn't there",3),
 T("tidal-ai-ban","Tidal announces ban on AI-generated music; 27 million tracks will be deleted","music",
   "Tidal will delete all 27 million AI-labeled tracks, 6.3% of its catalog, on Dec. 9; it says 96% of them got zero plays in the past 90 days, and 60% of new uploads on Nov. 6 were AI-generated.",
   "27 million songs nobody played. Ask the kids if they can even tell AI music anymore.",
   "https://arstechnica.com/ai/2026/11/tidal-will-ban-fully-ai-generated-music-on-december-9/","Ars Technica \u00b7 Nov 24","Tidal deleting 27M AI songs","Tidal's AI music purge",
   "Tidal is deleting 27 million AI-made songs on Dec. 9, and 96% never got a single play",4),
]
d['tech']={"origin":"wires","issue":None,"searchedAt":"2026-11-25T06:10:00-06:00",
 "note":"No Fast Company Daily issue found in the last 48 h: searched Drew's Gmail read-only on Nov 25, 2026 at 6:10 AM CT (drew@drewlentz.com, then drew@politiquera.com) for (from:fastcompany OR subject:\"Fast Company Daily\") newer_than:2d. National items are the fallback from the tech wires (The Verge, TechCrunch, Ars Technica); RGV tech items come first from local outlets.",
 "items":[
  {"id":"starbase-dc-vote","title":"Elon Musk\u2019s SpaceX Data Centers Face Key Votes on Same Day in December","short":"Starbase data center vote Dec 9","source":"Newsweek","source_url":"https://www.newsweek.com/elon-musks-spacex-data-centers-face-key-votes-on-same-day-in-december-12764916","published":"Nov 24",
   "one_line":"Starbase's City Commission is scheduled to consider a 10-year, 100% property tax abatement on Dec. 9 for SpaceX's $24 billion, 444-acre data center near Brownsville, after Cameron County voted 3-2 against tax-break talks. SpaceX says it has created 3,000-plus construction jobs, with 500-plus permanent jobs coming, and pledged $200 million for Brownsville water and wastewater.",
   "angle":"The data center the RGV Broadband Coalition's benefit-agreement template was written for. Will Starbase ask for any of it?","hook":"SpaceX's $24 billion data center tax break moves to Starbase's Dec. 9 vote","energy":4,"verified":True,"confirm":"","links":[],"basis":"Newsweek \u00b7 RGV Tech","valley":True},
  {"id":"stc-solis-ai","title":"Solis: AI will not replace workers, but workers who know how to use AI will","short":"STC: learn AI or get passed","source":"Rio Grande Guardian","source_url":"https://riograndeguardian.com/stories/solis-ai-will-not-replace-workers-but-workers-who-know-how-to-use-ai-will,91689","published":"Nov 24",
   "one_line":"At STC's Annual Workforce Summit, President Ricardo Solis called the Valley's problem a 'skills challenge' driven by AI and industrial growth, said people who know AI will replace those who don't, and said STC is ramping up electronics, precision manufacturing and mechatronics training.",
   "angle":"Drew's been preaching AI work bots for Valley businesses; now STC's president is saying it from the podium.","hook":"STC's president: AI won't replace you, but people who know AI will","energy":4,"verified":True,"confirm":"","links":[],"basis":"Rio Grande Guardian \u00b7 RGV Tech","valley":True},
  {"id":"vc-ai-scams","title":"'Stop, verify and protect': AI makes holiday scams harder to spot","short":"AI holiday scams: stop, verify","source":"ValleyCentral","source_url":"https://www.valleycentral.com/news/local-news/stop-verify-and-protect-ai-makes-holiday-scams-harder-to-spot/","published":"Nov 24",
   "one_line":"ValleyCentral (McAllen) reports holiday shopping scams are more convincing as criminals use AI to impersonate trusted organizations and build fake websites; a McAfee survey found 42% of Americans said they fell for a holiday shopping scam this year, nearly double last year's rate.",
   "angle":"Black Friday is Friday. Family rule: no paying through a link somebody texted you.","hook":"42% say they fell for a holiday shopping scam this year, and AI is making them harder to spot","energy":3,"verified":True,"confirm":"ValleyCentral blocks our reader; summary from the ValleyCentral feed","links":[],"basis":"ValleyCentral \u00b7 RGV Tech","valley":True},
  {"id":"ms-code-red","title":"Microsoft declares \u201cCode Red\u201d after huge Outlook outage","short":"Microsoft 'Code Red' after Outlook outage","source":"The Verge","source_url":"https://www.theverge.com/news/1042025/microsoft-code-red-outlook-outage","published":"Nov 25",
   "one_line":"After a huge Outlook outage, Microsoft is holding daily meetings with the engineering group responsible for Microsoft 365 services to cut down outage times.",
   "angle":"Every Valley office that runs on Outlook felt that one. Daily meetings: welcome to IT life.","hook":"Microsoft hits 'Code Red' after a huge Outlook outage","energy":3,"verified":True,"confirm":"Only the headline, deck and opening read","links":[]},
  {"id":"amazon-drone-garage","title":"Amazon drone crashes on garage after delivering shampoo, draws FAA probe","short":"Amazon drone crashes into garage","source":"Ars Technica","source_url":"https://arstechnica.com/gadgets/2026/11/faa-opens-probe-after-amazon-delivery-drone-clips-cable-crashes-into-garage/","published":"Nov 24",
   "one_line":"An Amazon Prime Air MK30 drone delivered shampoo in seven minutes to a Michigan backyard, then caught a propeller on a fiber-optic cable, hit a garage and tangled in power lines; the FAA opened a probe.",
   "angle":"Seven-minute shampoo, taken out by a fiber line. Somebody tell the drone fiber is good for you.","hook":"Seven-minute drone delivery, then a crash into the garage: the FAA is investigating","energy":4,"verified":True,"confirm":"","links":[]},
  {"id":"tiktok-down","title":"TikTok was down","short":"TikTok outage Tuesday","source":"The Verge","source_url":"https://www.theverge.com/tech/1041618/tiktok-down-outage","published":"Nov 24",
   "one_line":"TikTok had problems Tuesday, with videos, search results and favorites not loading normally, following a slew of other outages over the past couple of weeks.",
   "angle":"If your teenager suddenly talked to you Tuesday, now you know why.","hook":"It wasn't just your kid: TikTok was down Tuesday","energy":3,"verified":True,"confirm":"","links":[]},
 ]}
# sports
s=d['sports']
s['highSchool']['round']="Regional semifinals Friday, Nov. 27: Vela, PSJA North and La Villa alive (no RGV playoff games since Saturday Nov 21)"
s['highSchool']['sourceNote']="KRGV regional-semifinal preview of PSJA North (Nov 24) and last week's RGVSports/ValleyCentral matchups. No new RGV games since Saturday Nov 21; confirm Friday kickoff times before air."
s['highSchool']['next']=[{"title":"RGV high school football regional semifinal preview: PSJA North Raiders","short":"PSJA North regional semi preview","url":"https://www.krgv.com/news/rgv-high-school-football-regional-semifinal-preview-psja-north-raiders","source":"KRGV \u00b7 Nov 24","confirm":"Opponent, time and site not read; CONFIRM BEFORE AIR"}]+[x for x in s['highSchool'].get('next',[]) if 'psja-north-raiders' not in x.get('url','')][:3]
s['nfl']={"title":"NFL Week 12: Packers at Rams tonight; Thanksgiving tripleheader","scoreSource":{"title":"NFL.com Monday Night Football schedule (final)","short":"","url":"https://www.nfl.com/schedules/2026/prime-time/monday-night-football","source":"NFL.com"},
 "scores":[["Mon Nov 23","WAS 22, CIN 20 (MNF)"],["Sun Nov 22","DAL 51, TEN 30"],["Sun Nov 22","SF 35, MIN 10 (Mexico City)"]],
 "notable":[{"title":"Steelers bench Aaron Rodgers; Mason Rudolph starts Black Friday vs. Broncos","short":"Rodgers benched","url":"https://www.cbssports.com/nfl/news/steelers-bench-aaron-rodgers-make-qb-inactive-friday-broncos/","source":"CBS Sports \u00b7 Nov 24"},
  {"title":"Thanksgiving Eve: Packers at Rams tonight; Thursday: Bears at Lions, Eagles at Cowboys, Chiefs at Bills","short":"GB@LAR Wed; CHI@DET, PHI@DAL, KC@BUF Thu","url":"https://www.cbssports.com/betting/news/rams-packers-prediction-odds-start-time-2026-nfl-thanksgiving-eve-game-picks/","source":"CBS Sports \u00b7 Nov 24"}]}
n=s['nba']
n['scoreSource']={"title":"ESPN NBA scoreboard, Tue Nov 24","short":"","url":"https://www.espn.com/nba/scoreboard/_/date/20261124","source":"ESPN"}
n['scores']=[["Tue Nov 24","DAL 120, DEN 101"],["Tue Nov 24","BOS 131, WSH 116"],["Tue Nov 24","DET 104, ORL 86"],["Mon Nov 23","SAS 123, SAC 107"],["Mon Nov 23","HOU 116, LAC 104"]]
n['texas']=[["Tue Nov 24","DAL 120, DEN 101"],["Mon Nov 23","SAS 123, SAC 107"],["Mon Nov 23","HOU 116, LAC 104"]]
n['notable']=[{"title":"Cooper Flagg has 24 points and 12 assists as Mavericks beat Nuggets 120-101 in NBA Cup contest","short":"Mavs 120, Nuggets 101; Flagg 24/12","url":"https://www.espn.com/nba/game/_/gameId/401909316/mavericks-nuggets","source":"ESPN/AP \u00b7 Nov 24"},
 {"title":"Tatum scores 41 to help Celtics snap 4-game skid with a 131-116 win over Wizards","short":"Tatum 41, Celtics 131-116","url":"https://www.espn.com/nba/game/_/gameId/401909315/celtics-wizards","source":"ESPN/AP \u00b7 Nov 24"},
 {"title":"Without Cade Cunningham, Pistons get 21 from Isaiah Joe to hand Magic their first NBA Cup loss","short":"Pistons 104, Magic 86","url":"https://www.espn.com/nba/game/_/gameId/401909314/pistons-magic","source":"ESPN/AP \u00b7 Nov 24"}]
d['leads']=[]
d['chisme']={}
o=json.load(open('/tmp/obits.json')); d['obituaries']=o
for k in ['up_to','up_to_script','up_to_meta','up_to_coming']: d.pop(k,None)
json.dump(d,open(P+'packet-2026-11-25.json','w'),indent=1,ensure_ascii=False)
print('ok',len(rgv),len(tx))
# --- applied after the first run (kept here for reproducibility); then rerun chisme.py and family_calendar.py --merge ---
d=json.load(open(P+'packet-2026-11-25.json'))
r=d['headlines']['rgv']; i=[k for k,h in enumerate(r) if 'SpaceX Data Centers' in h['title']][0]; r.insert(3,r.pop(i))
d['headlines']['image']={"file":"assets/starship_thumb.jpg","caption":"File photo: Starship (Steve Jurvetson, CC BY 2.0, Wikimedia Commons)","credit_url":"https://commons.wikimedia.org/wiki/File:SpaceX_Starship_before_IFT-5.jpg","forItem":3}
# Starlink BEAD item (Fortune, Nov 17; r/texas lead) appended to headlines.texas: see packet JSON
json.dump(d,open(P+'packet-2026-11-25.json','w'),indent=1,ensure_ascii=False)
# energy tweaks: Plebe-giving 4; tech: vc-ai-scams 4, amazon-drone-garage 3, ms-code-red 3; tiktok-down dropped (tech cap is 5)
