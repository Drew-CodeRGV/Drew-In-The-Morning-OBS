const puppeteer=require('puppeteer-core');
const file=process.argv[2];
(async()=>{
 const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--disable-gpu'],headless:'new'});
 const errs=[];
 async function open(w,h,ua,ts){
  const p=await b.newPage(); await p.setViewport({width:w,height:h,deviceScaleFactor:2,isMobile:!!ua,hasTouch:!!ua});
  if(ua)await p.setUserAgent(ua);
  p.on('pageerror',e=>errs.push('pageerror '+e.message)); p.on('console',m=>{if(m.type()==='error')errs.push('console '+m.text())});
  await p.setRequestInterception(true); p.on('request',r=>{ if(r.url().startsWith('file:')) r.continue(); else r.abort()});
  await p.evaluateOnNewDocument((ts)=>{const RD=Date;let off=0;window.__set=(ms)=>{off=ms-RD.now()};
    if(ts){off=ts-RD.now();}
    window.Date=class extends RD{constructor(...a){if(a.length)super(...a);else super(RD.now()+off)}static now(){return RD.now()+off}};},ts||0);
  await p.goto('file://'+file); return p;
 }
 const IPAD='Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1';
 for(const [w,h] of [[768,1024],[820,1180],[1024,768],[1180,820],[1366,1024],[1440,900]]){
  const p=await open(w,h,IPAD);
  const r=await p.evaluate(()=>({sw:document.documentElement.scrollWidth,iw:innerWidth,minUse:Math.min(...[...document.querySelectorAll('.use')].map(b=>Math.min(b.offsetWidth,b.offsetHeight))),n:document.querySelectorAll('.use').length,fs:parseFloat(getComputedStyle(document.documentElement).fontSize)}));
  console.log(w+'x'+h,JSON.stringify(r), r.sw<=r.iw?'OK':'H-SCROLL');
  if(w==768||w==1180) await p.screenshot({path:`/workspace/_pt/ipad-${w}.png`});
  await p.close();
 }
 // show-start test: Mon Nov 23 2026 09:03:30 CT = 15:03:30Z
 const T0=Date.UTC(2026,10,23,15,3,30);
 let p=await open(1180,820,null,T0);
 const g=()=>p.evaluate(()=>({ind:document.getElementById('ssind').textContent,live:document.getElementById('sslive').textContent,cw:document.getElementById('cwnext').innerText.replace(/\n/g,' '),cls:document.getElementById('cwnext').className,r:[...document.querySelectorAll('.tr')].slice(0,4).map(x=>x.dataset.range||x.querySelector('b').textContent+'|'+x.querySelector('small').textContent)}));
 console.log('before click',JSON.stringify(await g()));
 await p.click('#ssbtn'); console.log('after click',JSON.stringify(await g()));
 await p.reload(); console.log('after reload',JSON.stringify(await g()));
 // advance to 09:06:50 (in block C: 9:05-9:13 => next D) 
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,15,6,50)); await new Promise(r=>setTimeout(r,1200));
 console.log('09:06:50',JSON.stringify(await g()));
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,15,12,50)); await new Promise(r=>setTimeout(r,1200));
 console.log('09:12:50',JSON.stringify(await g()));
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,15,12,58)); await new Promise(r=>setTimeout(r,1200));
 console.log('09:12:58 (amber/red)',JSON.stringify(await g()));
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,16,0,20)); await new Promise(r=>setTimeout(r,1200));
 console.log('10:00:20 final block',JSON.stringify(await g()));
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,16,4,20)); await new Promise(r=>setTimeout(r,1200));
 console.log('10:04:20 over',JSON.stringify(await g()));
 await p.evaluate((ms)=>window.__set(ms),Date.UTC(2026,10,23,15,6,50)); await new Promise(r=>setTimeout(r,1200));
 await p.screenshot({path:'/workspace/_pt/live.png'});
 await p.click('#ssreset'); console.log('reset',JSON.stringify(await g()));
 await p.close();
 // before show on show day 7:55 CT = 13:55Z unstarted
 p=await open(1180,820,null,Date.UTC(2026,10,23,13,55,0)); console.log('07:55 unstarted',JSON.stringify(await g())); await p.close();
 // toggles
 p=await open(1180,820,null,T0);
 await p.evaluate(()=>{document.querySelector('#headlines .use').click()});
 console.log('used',await p.evaluate(()=>document.getElementById('ucount').textContent+' '+document.getElementById('usedul').innerText.slice(0,120)));
 await p.reload(); console.log('used after reload',await p.evaluate(()=>document.getElementById('ucount').textContent));
 await p.close();

 // ---------- collapsed-by-default dashboard + breaking strip (served over http so same-origin fetch works) ----------
 const http=require('http'),fs=require('fs'),path=require('path');
 const root=process.argv[3]||path.dirname(file);               // dir that contains packets/ and breaking.json
 const pkt=process.argv[4]||file;                              // the studio html to test
 let mode='ok', hits=0;
 const srv=http.createServer((q,r)=>{
   const u=q.url.split('?')[0];
   if(u==='/breaking.json'){hits++; if(mode==='404'){r.statusCode=404;return r.end('no')}
     const built=Date.parse(fs.readFileSync(pkt,'utf8').match(/data-built="([^"]*)"/)[1])||Date.now();
     const iso=(m)=>new Date(built+m*60000).toISOString();
     r.setHeader('content-type','application/json');
     return r.end(JSON.stringify({version:1,generatedAt:iso(30),bootstrap:false,feeds:{ok:14,failed:5,total:19},items:[
       {id:'a1',title:'TEST: Fire evacuates McAllen apartment complex <b>x</b>',url:'https://example.com/a',source:'KRGV',sources:[{name:'KRGV'},{name:'ValleyCentral'}],level:'alert',label:'Hot',score:51,firstSeen:iso(10),matches:['McAllen','fire'],uncovered:false},
       {id:'a2',title:'TEST: Community buzz about Edinburg road closure',url:'javascript:alert(1)',source:'r/RGV',sources:[{name:'r/RGV'}],level:'watch',label:'Active',score:19,firstSeen:iso(20),matches:['Edinburg'],uncovered:true},
       {id:'o1',title:'TEST: older item from before the build',url:'https://example.com/o',source:'Monitor',sources:[{name:'Monitor'}],level:'watch',label:'Trending',score:30,firstSeen:iso(-120),matches:[],uncovered:false}]}));}
   let f=path.join(root,u==='/'?'/index.html':u); if(!f.startsWith(root)){r.statusCode=403;return r.end()}
   fs.readFile(f,(e,b)=>{if(e){r.statusCode=404;return r.end('nf')} r.setHeader('content-type',f.endsWith('.html')?'text/html':f.endsWith('.json')?'application/json':'application/octet-stream');r.end(b)});
 }).listen(0);
 await new Promise(r=>srv.on('listening',r));
 const base='http://127.0.0.1:'+srv.address().port;
 const rel='/'+path.relative(root,pkt).split(path.sep).join('/');
 async function openHttp(w,h,ua,q){
  const p=await b.newPage(); await p.setViewport({width:w,height:h,deviceScaleFactor:2,isMobile:!!ua,hasTouch:!!ua}); if(ua)await p.setUserAgent(ua);
  p.on('pageerror',e=>errs.push('pageerror '+e.message)); p.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text()))errs.push('console '+m.text())});
  await p.goto(base+rel+(q||''),{waitUntil:'load'}); return p;
 }
 const st=(p)=>p.evaluate(()=>{const d=[...document.querySelectorAll('details')];const secs=[...document.querySelectorAll('details.sec')];return {total:d.length,open:d.filter(x=>x.open).length,secs:secs.length,secOpen:secs.filter(x=>x.open).length,
   sw:document.documentElement.scrollWidth,iw:innerWidth,minHdr:Math.min(...secs.map(x=>x.querySelector('summary').getBoundingClientRect().height)),
   hdrVisible:secs.every(x=>x.querySelector('summary').getBoundingClientRect().width>100),
   clockVisible:!!document.getElementById('cwnext')&&document.getElementById('cwnext').offsetHeight>0,ssbtn:!!document.getElementById('ssbtn')&&document.getElementById('ssbtn').offsetHeight>0,
   brkVisible:document.getElementById('brk').offsetHeight>0}});
 const fails=[]; const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m); if(!c)fails.push(m)};
 {
  const p0=await openHttp(1180,820,IPAD);
  const t=await p0.evaluate(()=>{const e=document.getElementById('tech');return e?{open:e.open,items:e.querySelectorAll('.sortbox>.item.trn').length,links:[...e.querySelectorAll('.sortbox>.item.trn>.tx>b a[href^="http"]')].length,badge:(e.querySelector('summary').textContent||'').includes('TECH'),nav:!!document.querySelector('nav a[href="#tech"]'),hdr:e.querySelector('summary').getBoundingClientRect().height}:null});
  ok(!!t,'Tech section exists'); if(t){ ok(!t.open,'Tech section starts collapsed'); ok(t.items>=3&&t.items<=5,'Tech section has 3-5 items ('+t.items+')'); ok(t.links>=t.items,'every Tech item links to its article'); ok(t.badge&&t.nav&&t.hdr>=44,'Tech header badge, nav link and 44px+ target'); }
  const jr=await p0.evaluate(()=>{const j=document.getElementById('blk-J');return j?j.textContent.includes('TECH SUB-SEGMENT')&&j.textContent.includes('quick tech check'):false});
  ok(jr,'Block J (rundown) carries the Tech sub-segment and its segue');
  const ob=await p0.evaluate(()=>{const e=document.getElementById('obits');if(!e)return null;const L=document.getElementById('blk-L');const all=[...e.querySelectorAll('.ob a')];return {open:e.open,links:all.filter(a=>/^https:\/\/www\.legacy\.com\//.test(a.href)).length,n:all.length,nav:!!document.querySelector('nav a[href="#obits"]'),hdr:e.querySelector('summary').getBoundingClientRect().height,script:!!e.querySelector('#obscript'),lread:L?/neighbors/i.test(L.textContent):false,cause:/cancer|cause of death|died of/i.test(e.textContent)}});
  ok(!!ob,'Remembering Our Neighbors section exists'); if(ob){ ok(!ob.open,'Neighbors section starts collapsed'); ok(ob.n>0&&ob.links===ob.n,'every neighbor name links to its Legacy obituary ('+ob.links+'/'+ob.n+')'); ok(ob.nav&&ob.hdr>=44&&ob.script,'Neighbors nav link, 44px+ header and on-air read'); ok(ob.lread,'Block L carries the obituary read'); ok(!ob.cause,'no cause of death anywhere in the obituary section'); }
  const ut=await p0.evaluate(()=>{const e=document.getElementById('blk-B');if(!e)return null;return {open:e.open,text:e.textContent,script:(document.getElementById('uptotext')||{}).textContent||''}});
  ok(!!ut&&!ut.open,'Block B (Up To) starts collapsed'); if(ut){ ok(/family calendar/i.test(ut.text),'Block B is sourced from the family calendar'); ok(!/proposal|conference|gmail|CONFIRM/i.test(ut.script),'Block B script has no conference/Gmail/CONFIRM wording'); }
  await p0.close();
 }
 for(const [w,h] of [[768,1024],[820,1180],[1024,768],[1180,820],[1366,1024]]){
  const p=await openHttp(w,h,IPAD); await new Promise(r=>setTimeout(r,500));
  let s=await st(p);
  ok(s.open===0,`${w}x${h} everything collapsed on load (open details: ${s.open}/${s.total})`);
  ok(s.sw<=s.iw,`${w}x${h} no horizontal scroll collapsed (${s.sw}<=${s.iw})`);
  ok(s.minHdr>=44,`${w}x${h} section header targets >= 44px (min ${Math.round(s.minHdr)})`);
  ok(s.clockVisible&&s.ssbtn&&s.brkVisible,`${w}x${h} clock, countdown, Show Start and Breaking strip visible while collapsed`);
  await p.click('#expand'); await new Promise(r=>setTimeout(r,200)); s=await st(p);
  ok(s.open===s.total,`${w}x${h} Expand all opens everything (${s.open}/${s.total})`);
  ok(s.sw<=s.iw,`${w}x${h} no horizontal scroll expanded (${s.sw}<=${s.iw})`);
  if(w===768||w===1180) await p.screenshot({path:`/workspace/_pt/expanded-${w}.png`,fullPage:true});
  await p.click('#collapse'); await new Promise(r=>setTimeout(r,200)); s=await st(p);
  ok(s.open===0,`${w}x${h} Collapse all closes everything (${s.open})`);
  if(w===768||w===1180) await p.screenshot({path:`/workspace/_pt/collapsed-${w}.png`,fullPage:true});
  await p.close();
 }
 {
  const p=await openHttp(1180,820,IPAD);
  await p.evaluate(()=>{});
  // tap one header -> opens; reload keeps it (session) ; new page (new tab, fresh sessionStorage) -> collapsed again
  await p.tap('#headlines > summary'); await new Promise(r=>setTimeout(r,200));
  ok(await p.evaluate(()=>document.getElementById('headlines').open),'tap on a section header opens it');
  const tapH=await p.evaluate(()=>document.querySelector('#headlines > summary').getBoundingClientRect().height); ok(tapH>=44,'header tap height '+Math.round(tapH));
  await p.evaluate(()=>document.querySelector('#blk-C > summary').click());
  await p.reload({waitUntil:'load'});
  ok(await p.evaluate(()=>document.getElementById('headlines').open),'same session: opened section stays open after reload');
  const rdOpen=await p.evaluate(()=>{const c=document.getElementById('blk-C');return [c&&c.open]}); console.log('block C open after reload',JSON.stringify(rdOpen));
  const pg=await b.newPage(); await pg.setViewport({width:1180,height:820}); await pg.goto(base+rel,{waitUntil:'load'});
  ok(await pg.evaluate(()=>[...document.querySelectorAll('details')].every(d=>!d.open)),'fresh tab/session starts fully collapsed'); await pg.close();
  // jump link from nav opens its section
  await p.evaluate(()=>{[...document.querySelectorAll('details')].forEach(d=>d.open=false)});
  const nav=await p.evaluate(()=>[...document.querySelectorAll('nav a')].map(a=>a.getAttribute('href')+'|'+a.textContent).slice(0,3)); console.log('nav',JSON.stringify(nav));
  // sort toggle
  const firstTitles=()=>p.evaluate(()=>[...document.querySelectorAll('#national .sortbox > .item')].map(d=>d.dataset.sc+'/'+d.dataset.ord));
  const t1=await firstTitles(); await p.click('#sortbtn'); const t2=await firstTitles(); await p.click('#sortbtn');
  console.log('national order score->editorial',JSON.stringify(t1),JSON.stringify(t2));
  ok(JSON.stringify(t1)!==JSON.stringify(t2)||t1.length<2,'sort button changes order (or <2 items)');
  // breaking strip
  await new Promise(r=>setTimeout(r,800));
  const bs=await p.evaluate(()=>({count:document.getElementById('brkcount').textContent,badge:document.getElementById('brkb').textContent,meta:document.getElementById('brkmeta').textContent,rows:document.querySelectorAll('#brklist .brkrow').length,
     links:[...document.querySelectorAll('#brklist a')].map(a=>a.href),html:document.getElementById('brklist').innerHTML.includes('<b>x</b>'),unc:document.getElementById('brklist').textContent.includes('CONFIRM BEFORE AIR')}));
  console.log('breaking',JSON.stringify(bs));
  ok(bs.count==='2'&&bs.badge==='2','breaking strip counts items newer than the build (2) and badge matches');
  ok(bs.rows===2,'two NEW rows shown, older one hidden behind a button');
  ok(!bs.html,'titles are inserted as text (no HTML injection)');
  ok(bs.links.every(u=>/^https?:/.test(u))&&bs.links.length===1,'unsafe javascript: URL is not made a link');
  ok(bs.unc,'Uncovered item is marked CONFIRM BEFORE AIR');
  await p.screenshot({path:'/workspace/_pt/breaking-1180.png'});
  // polling: shorten poll through the dataset is fixed at build (120s); verify the timer exists by forcing refresh button and counting hits
  const h0=hits; await p.click('#brkref'); await new Promise(r=>setTimeout(r,500)); ok(hits>h0,'Refresh button re-fetches breaking.json');
  console.log('poll interval attr',await p.evaluate(()=>document.getElementById('brk').dataset.poll)+'s');
  mode='404'; await p.click('#brkref'); await new Promise(r=>setTimeout(r,600));
  ok((await p.evaluate(()=>document.getElementById('brkmeta').textContent)).includes('Could not refresh'),'fetch failure keeps last data and says so');
  await p.close();
 }
 {
  const p=await b.newPage(); await p.evaluateOnNewDocument(()=>{window.__iv=[];const si=window.setInterval;window.setInterval=function(f,d){window.__iv.push(d);return si.apply(this,arguments)}});
  await p.goto(base+rel,{waitUntil:'load'}); ok((await p.evaluate(()=>window.__iv)).includes(120000),'breaking.json poll runs every 120000 ms (intervals: '+JSON.stringify(await p.evaluate(()=>window.__iv))+')'); await p.close();
 }

 // ---------- layout v6: phone scrolling, uniform tiles, full-width expanded sections, Trending News rename ----------
 const SHOTS='/workspace/ditm-shots'; fs.mkdirSync(SHOTS,{recursive:true});
 const IPHONE='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
 const delay=(ms)=>new Promise(r=>setTimeout(r,ms));
 const fullbars=(u,tag)=>{ok(u.dfull<=2,`${tag} every collapsed section is full container width (${u.inner}px; max diff ${u.dfull.toFixed(1)}px)`);ok(u.lefts===1&&u.stacked,`${tag} one bar per row, stacked (${u.lefts} left edge)`);ok(u.trunc.length===0,`${tag} no truncated titles/subtitles at wide widths ${JSON.stringify(u.trunc)}`)};
 const uniform=(p)=>p.evaluate(()=>{const secs=[...document.querySelectorAll('details.sec')];const hs=secs.map(x=>x.querySelector('summary').getBoundingClientRect());const ws=hs.map(r=>r.width),hh=hs.map(r=>r.height);
   const m=document.querySelector('main'),cs=getComputedStyle(m),inner=m.getBoundingClientRect().width-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
   const lefts=new Set(secs.map(x=>Math.round(x.getBoundingClientRect().left)));const tops=secs.map(x=>x.getBoundingClientRect().top);const stacked=tops.every((t,i)=>i===0||t>tops[i-1]);
   const wide=window.innerWidth>=700;const trunc=wide?[...document.querySelectorAll('details.sec>summary .tn,details.sec>summary small')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.slice(0,30)):[];
   const rows=secs.map(x=>x.getBoundingClientRect().width);
   return {n:hs.length,dh:Math.max(...hh)-Math.min(...hh),dw:Math.max(...ws)-Math.min(...ws),h:Math.round(hh[0]),inner:Math.round(inner),dfull:Math.max(...rows.map(w=>Math.abs(w-inner))),lefts:lefts.size,stacked,trunc}});
 for(const [w,h] of [[360,740],[390,844],[412,915],[430,932]]){
  const p=await openHttp(w,h,IPHONE); await delay(500);
  const r=await p.evaluate(()=>{const cs=getComputedStyle,de=document.documentElement,bd=document.body;
    const pinned=[...document.querySelectorAll('body *')].filter(e=>{const c=cs(e);return (c.position==='sticky'||c.position==='fixed')&&c.display!=='none'&&e.id!=='toast'&&e.offsetHeight>0});
    const tg=[...document.querySelectorAll('button,nav a,summary,.btnlike,#minibar a')].filter(e=>e.offsetWidth>0&&e.offsetHeight>0&&!e.closest('details:not([open]) .body')&&!e.closest('.body'));
    const small=tg.filter(e=>Math.min(e.getBoundingClientRect().width,e.getBoundingClientRect().height)<43.5).map(e=>(e.id||e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height));
    return {ovH:[cs(de).overflowY,cs(bd).overflowY],hh:[de.style.height||cs(de).height==='auto',cs(bd).height==='auto'||cs(bd).height===de.getBoundingClientRect().height+'px'],docH:de.scrollHeight,vh:innerHeight,pinned:pinned.map(e=>e.tagName+'#'+e.id+':'+e.offsetHeight),pinnedH:pinned.reduce((a,e)=>a+e.offsetHeight,0),sw:de.scrollWidth,iw:innerWidth,small,
      hasMini:!!document.getElementById('minibar')&&document.getElementById('minibar').offsetHeight>0,time:cs(de).touchAction}});
  ok(r.ovH.every(v=>v!=='hidden'&&v!=='clip'),`${w}x${h} html/body do not clip or lock vertical scrolling (${r.ovH})`);
  ok(r.docH>r.vh*1.5,`${w}x${h} document is taller than the screen (${r.docH} vs ${r.vh}) so it must scroll`);
  ok(r.pinnedH<=110&&r.pinnedH<=r.vh*0.16,`${w}x${h} pinned (sticky/fixed) chrome is short: ${r.pinnedH}px of ${r.vh}px (${r.pinned})`);
  ok(r.sw<=r.iw,`${w}x${h} no horizontal overflow (${r.sw}<=${r.iw})`);
  ok(!/none/.test(r.time),`${w}x${h} touch-action allows scrolling (${r.time})`);
  ok(r.small.length===0,`${w}x${h} tap targets >= 44px ${r.small.slice(0,6)}`);
  const drag=async(y0,dy)=>{await p.touchscreen.touchStart(Math.round(w/2),y0);for(let i=1;i<=10;i++)await p.touchscreen.touchMove(Math.round(w/2),y0+Math.round(dy*i/10));await p.touchscreen.touchEnd();await delay(600)};
  await drag(Math.round(h*0.7),-Math.round(h*0.3));
  const y1=await p.evaluate(()=>scrollY); ok(y1>100,`${w}x${h} real touch drag scrolls the document (scrollY ${Math.round(y1)})`);
  await drag(Math.round(h*0.4),Math.round(h*0.15));
  ok(await p.evaluate((y)=>scrollY<y,y1),`${w}x${h} dragging back scrolls up`);
  await p.evaluate(()=>scrollTo(0,0)); await delay(100);
  const u=await uniform(p); ok(u.dh<=2&&u.dw<=2,`${w}x${h} all ${u.n} collapsed section headers are the same size (height diff ${u.dh.toFixed(1)}px, width diff ${u.dw.toFixed(1)}px, ${u.h}px tall)`);fullbars(u,`${w}x${h}`);
  const tlr=await p.evaluate(()=>{const c=document.querySelector('.clock');return {fit:c.scrollWidth<=c.clientWidth+1,h:c.getBoundingClientRect().height,letters:[...c.querySelectorAll('a')].every(a=>a.getBoundingClientRect().width>=8),n:c.querySelectorAll('a').length}}); ok(tlr.fit&&tlr.n===12&&tlr.letters,`${w}x${h} A-L timeline fits the full width with no swiping (12 segments)`); ok(tlr.h>=32&&tlr.h<=40,`${w}x${h} timeline is compact (${tlr.h}px)`);
  await p.click('#expand'); await delay(300);
  const e=await p.evaluate(()=>({sw:document.documentElement.scrollWidth,iw:innerWidth,cols:new Set([...document.querySelectorAll('#headlines .sortbox>.item')].map(x=>Math.round(x.getBoundingClientRect().left))).size}));
  ok(e.sw<=e.iw,`${w}x${h} no horizontal overflow with everything expanded (${e.sw}<=${e.iw})`); ok(e.cols===1,`${w}x${h} phone shows one column of story cards (${e.cols})`);
  if(w===390){await p.click('#collapse');await delay(200);await p.screenshot({path:SHOTS+'/v2-phone-390x844-collapsed.png'});
    await p.evaluate(()=>{const d=document.getElementById('headlines');d.open=true;scrollTo(0,d.getBoundingClientRect().top+scrollY-50)});await delay(300);await p.screenshot({path:SHOTS+'/v2-phone-390x844-headlines-open.png'});}
  await p.close();
 }
 for(const [w,h,ua,name] of [[768,1024,IPAD,'ipad-portrait-768x1024'],[820,1180,IPAD,'ipad-portrait-820x1180'],[1024,768,IPAD,'ipad-landscape-1024x768'],[1180,820,IPAD,'ipad-landscape-1180x820'],[1280,800,null,'macbook-1280x800'],[1440,900,null,'macbook-1440x900']]){
  const p=await openHttp(w,h,ua); await delay(500);
  const u=await uniform(p); ok(u.dh<=2&&u.dw<=2,`${w}x${h} all ${u.n} collapsed section headers are the same size (height diff ${u.dh.toFixed(1)}px, width diff ${u.dw.toFixed(1)}px)`);fullbars(u,`${w}x${h}`);
  const cols=await p.evaluate(()=>{const m=document.querySelector('main');return new Set([...document.querySelectorAll('details.sec')].map(x=>Math.round(x.getBoundingClientRect().left))).size});
  await p.screenshot({path:`${SHOTS}/v2-${name}-collapsed.png`});
  const sticky=await p.evaluate(()=>{const e=document.getElementById('pin');return getComputedStyle(e).position==='sticky'?e.offsetHeight:9999});
  ok(sticky<=110,`${w}x${h} pinned bar (clock row + timeline) is compact (${sticky}px)`);
  for(const id of ['headlines','trending','national','memes','blk-C','chisme']){
    await p.evaluate((id)=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);document.getElementById(id).open=true},id); await delay(150);
    const g=await p.evaluate((id)=>{const d=document.getElementById(id),m=document.querySelector('main'),cs=getComputedStyle(m),mr=m.getBoundingClientRect(),dr=d.getBoundingClientRect();
      const inner=mr.width-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
      const L=new Set([...d.querySelectorAll('.body .sortbox>.item')].map(x=>Math.round(x.getBoundingClientRect().left)));
      return {frac:dr.width/inner,cols:L.size,sw:document.documentElement.scrollWidth,iw:innerWidth}},id);
    ok(g.frac>=0.98,`${w}x${h} expanded ${id} fills the grid width (${(g.frac*100).toFixed(0)}%)`);
    ok(g.sw<=g.iw,`${w}x${h} expanded ${id} has no horizontal overflow`);
    if(id==='headlines'){ const want=w>=1280?3:w>=700?2:1; ok(g.cols>=want,`${w}x${h} Top Headlines story cards flow in ${g.cols} columns (>= ${want})`); }
  }
  await p.evaluate(()=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);const d=document.getElementById('headlines');d.open=true;scrollTo(0,d.getBoundingClientRect().top+scrollY-(document.querySelector('header').offsetHeight>0&&getComputedStyle(document.querySelector('header')).position==='sticky'?document.querySelector('header').offsetHeight+8:60))});
  await delay(300); await p.screenshot({path:`${SHOTS}/v2-${name}-headlines-open.png`}); await p.close();
 }
 {
  const p=await openHttp(1440,900,null); await delay(400);
  const txt=await p.evaluate(()=>document.documentElement.textContent);
  ok(!/wait,?\s*don['’]t tell me/i.test(txt),'"Wait, Don\'t Tell Me" does not appear anywhere on the studio page');
  const tr=await p.evaluate(()=>{const e=document.getElementById('trending');return {t:e.querySelector('.tn').textContent,sub:e.querySelector('summary small').textContent,riff:/riff material/i.test(e.querySelector('summary').textContent)}});
  ok(tr.t==='Trending News'&&/trending around the nation/i.test(tr.sub)&&!tr.riff,`Trending section is "${tr.t}" / "${tr.sub}"`);
  await p.close();
  for(const [w,h,name] of [[390,844,'phone'],[820,1180,'ipad'],[1180,820,'ipad-land'],[1440,900,'macbook']]){
    const q=await openHttp(w,h,w<500?IPHONE:w<1300?IPAD:null); await delay(300);
    await q.evaluate(()=>{const d=document.getElementById('headlines');d.open=true});await delay(200);
    await q.screenshot({path:`${SHOTS}/v2-headlines-open-${w}x${h}-full.png`,fullPage:true}); await q.close();
  }
 }

 // ---------- t57u-t60u: no Rundown section; A-L are sections; every section opens into Trending-model cards; Chisme; short Obituaries ----------
 const LET='ABCDEFGHIJKL'.split('');
 for(const [w,h,ua,tag] of [[390,844,IPHONE,'390'],[820,1180,IPAD,'820'],[1024,768,IPAD,'1024'],[1440,900,null,'1440']]){
  const p=await openHttp(w,h,ua); await delay(500);
  const base0=await p.evaluate(()=>({rd:!!document.getElementById('rundown'),txt:/monday 8 ?am rundown/i.test([...document.querySelectorAll('details.sec>summary,nav')].map(e=>e.textContent).join(' ')),nested:document.querySelectorAll('.sec .body details').length}));
  ok(!base0.rd&&!base0.txt,`${tag} the Monday 8 AM Rundown section is gone`); ok(base0.nested===0,`${tag} no nested expanders inside sections (${base0.nested})`);
  const order=await p.evaluate(()=>[...document.querySelectorAll('details.sec')].map(d=>d.id));
  const bl=order.filter(x=>/^blk-/.test(x)).map(x=>x.slice(4)).join('');
  ok(bl===LET.join(''),`${tag} blocks A-L each have their own section, in order (${bl})`);
  ok(order.indexOf('chisme')===order.indexOf('headlines')+1,`${tag} Chisme sits right after Top Headlines (${order.slice(order.indexOf('headlines')-1,order.indexOf('headlines')+3)})`);
  const u=await uniform(p); ok(u.dh<=2&&u.dw<=2,`${tag} all ${u.n} section bars are the same size (dh ${u.dh.toFixed(1)}, dw ${u.dw.toFixed(1)})`); fullbars(u,tag);
  ok(u.n===order.length&&u.n>=24,`${tag} ${u.n} section bars`);
  // every timeline segment opens and scrolls to its block
  for(const L of LET){
    await p.evaluate(()=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);scrollTo(0,0)}); await delay(60);
    await p.evaluate((L)=>document.querySelector('#tl a[data-jump="blk-'+L+'"]').click(),L); await delay(650);
    const j=await p.evaluate((L)=>{const d=document.getElementById('blk-'+L);const pin=document.getElementById('pin').getBoundingClientRect().bottom;return {open:d.open,top:d.getBoundingClientRect().top-pin,cards:d.querySelectorAll('.sortbox>.item.trn').length,only:[...document.querySelectorAll('details.sec')].filter(x=>x.open).length}},L);
    ok(j.open&&j.only===1&&j.cards>=3&&j.top>-3&&j.top<h*0.5,`${tag} tapping timeline ${L} opens only block ${L} (${j.cards} cards) and scrolls it into view (top ${Math.round(j.top)}px)`);
  }
  // every section's cards use the Trending model and are equal width in their grid
  const secs=await p.evaluate(()=>[...document.querySelectorAll('details.sec')].map(d=>d.id).filter(x=>x!=='used'&&x!=='obits'));
  for(const id of secs){
    await p.evaluate((id)=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);document.getElementById(id).open=true},id); await delay(120);
    const g=await p.evaluate((id)=>{const d=document.getElementById(id);const boxes=[...d.querySelectorAll('.body .sortbox')];const kids=boxes.flatMap(b=>[...b.children]).filter(c=>!c.classList.contains('noev'));
      const bad=kids.filter(c=>!c.classList.contains('item')||!c.classList.contains('trn')||!c.querySelector('.tx>b')).length;
      const wd=boxes.map(b=>{const ws=[...b.children].filter(c=>!c.classList.contains('noev')).map(c=>c.getBoundingClientRect().width);return ws.length?Math.max(...ws)-Math.min(...ws):0});
      const order=kids.filter(c=>c.querySelector('.tldr')&&c.querySelector('.ang')).filter(c=>c.querySelector('.tldr').compareDocumentPosition(c.querySelector('.ang'))&Node.DOCUMENT_POSITION_FOLLOWING?false:true).length;
      const lefts=new Set(kids.map(c=>Math.round(c.getBoundingClientRect().left))).size;
      const inner=d.querySelector('.body').getBoundingClientRect().width;
      return {n:kids.length,bad,wd:Math.max(0,...wd),order,lefts,sw:document.documentElement.scrollWidth,iw:innerWidth,fill:d.getBoundingClientRect().width,body:inner}},id);
    ok(g.n>0,`${tag} ${id}: opens into ${g.n} cards`);
    ok(g.bad===0,`${tag} ${id}: every item is a Trending-model card (headline + meta + TL;DR + Riff); ${g.bad} are not`);
    ok(g.wd<=2,`${tag} ${id}: cards in a grid are equal width (spread ${g.wd.toFixed(1)}px)`);
    ok(g.order===0,`${tag} ${id}: TL;DR always comes before Riff`);
    ok(g.sw<=g.iw,`${tag} ${id}: no horizontal overflow`);
    if(w<=500) ok(g.lefts===1,`${tag} ${id}: one column of cards on a phone (${g.lefts})`);
    else if(g.n>=4&&!['weather','hs','nfl','nba','mlb','memes'].includes(id)) ok(g.lefts>=(w>=1280?3:2),`${tag} ${id}: cards flow in ${g.lefts} columns`);
  }
  // card anatomy: Trending News is the model, headlines/national/blocks follow it
  const an=await p.evaluate(()=>{const o={};for(const id of ['trending','national','tech','headlines','memes']){const c=document.querySelector('#'+id+' .sortbox>.item.trn');const q=(s)=>c.querySelector(s);const kids=[...c.querySelector('.tx').children].map(e=>e.className||e.tagName);
      o[id]={head:!!q('.tx>b a'),meta:!!q('.src'),tldr:id==='headlines'?null:!!q('.tldr'),riff:id==='headlines'?null:!!q('.ang'),score:!!q('.sb')||id!=='trending'&&id!=='headlines'&&id!=='national'}}return o});
  for(const id of Object.keys(an)){const a=an[id];ok(a.head&&a.meta&&a.tldr!==false&&a.riff!==false,`${tag} ${id} card has headline, meta line${id==='headlines'?'':', TL;DR and Riff'} ${JSON.stringify(a)}`)}
  // chisme
  const cs=await p.evaluate(()=>{const e=document.getElementById('chisme');const cards=[...e.querySelectorAll('.sortbox>.item.trn')];
    return {sub:e.querySelector('summary small').textContent,title:e.querySelector('.tn').textContent,n:cards.length,links:cards.every(c=>/^https?:/.test((c.querySelector('.tx>b a')||{}).href||'')),
      badges:cards.map(c=>(c.querySelector('.cf')||c.querySelector('.sb.t')||{}).textContent||'?'),txt:e.textContent,riff:cards.some(c=>c.querySelector('.ang')),plat:cards.every(c=>c.querySelector('.pill')),nav:!!document.querySelector('nav a[href="#chisme"]'),
      badge:e.querySelector('summary .cf')?e.querySelector('summary .cf').textContent:''}});
  ok(cs.title==='Chisme'&&cs.sub==='what the Valley is buzzing about',`${tag} Chisme bar: "${cs.title}" / "${cs.sub}"`);
  ok(cs.n>=4&&cs.n<=10,`${tag} Chisme has ${cs.n} cards (4-10 in the fixture)`); ok(cs.links&&cs.plat&&cs.riff,`${tag} Chisme cards link to the original post, show the platform and carry a Riff`);
  ok(cs.badges.every(b=>/RUMOR · CONFIRM BEFORE AIR|CONFIRMED · /.test(b))&&cs.badges.some(b=>/RUMOR/.test(b)),`${tag} every Chisme card says RUMOR · CONFIRM BEFORE AIR unless a news outlet confirmed it (${cs.badges.length})`);
  ok(!/956-|address removed|\bteen\b|Maria Gonzalez/i.test(cs.txt)&&cs.nav&&/RUMOR/.test(cs.badge),`${tag} Chisme shows no phone/address/minor/private-name content; nav link and bar badge present`);
  // obituaries: newest 7 days by default, week before behind a button
  const ob0=await p.evaluate(()=>{const e=document.getElementById('obits');return {badge:e.querySelector('summary .cnt').textContent,small:e.querySelector('summary small').textContent}});
  const m=/^(\d+) this week · (\d+) in 2 weeks$/.exec(ob0.badge); ok(!!m,`${tag} obituaries bar badge reads "${ob0.badge}"`);
  await p.evaluate(()=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);document.getElementById('obits').open=true;document.getElementById('obits').scrollIntoView()}); await delay(250);
  const vis=()=>p.evaluate(()=>{const e=document.getElementById('obits');const v=[...e.querySelectorAll('.ob')].filter(x=>x.offsetParent!==null);const btn=document.getElementById('obmore'),pv=document.getElementById('obprev'),body=e.querySelector('.body');const bs=getComputedStyle(body);
    const inner=body.getBoundingClientRect().width-parseFloat(bs.paddingLeft)-parseFloat(bs.paddingRight);
    return {vis:v.length,all:e.querySelectorAll('.ob').length,hidden:pv.hidden,btn:btn.textContent,exp:btn.getAttribute('aria-expanded'),bw:btn.getBoundingClientRect().width,inner,bh:btn.getBoundingClientRect().height,
      bad:v.filter(x=>x.querySelector('.tldr,.ang,.upill')||/cause|died of|passed from/i.test(x.textContent)).length,stars:e.querySelectorAll('#obnew .obstar').length,
      fmt:v.every(x=>x.querySelector('a[href^="https://www.legacy.com/"]')&&/\d/.test(x.querySelector('.obm').textContent)),read:((document.getElementById('obscript')||document).querySelector('.tldr')||{}).textContent||'',sw:document.documentElement.scrollWidth,iw:innerWidth}});
  let o=await vis(); const wk=+m[1],tot=+m[2];
  ok(o.vis===wk&&o.hidden,`${tag} obituaries show ${o.vis} (the newest 7 days = ${wk}) by default; the previous week is hidden`);
  ok(o.btn===`Show the previous week (${tot-wk})`&&o.exp==='false',`${tag} button reads "${o.btn}"`);
  ok(Math.abs(o.bw-o.inner)<=2&&o.bh>=44,`${tag} the button is full width (${Math.round(o.bw)}/${Math.round(o.inner)}px) and 44px+ tall (${Math.round(o.bh)})`);
  ok(o.bad===0&&o.fmt,`${tag} obituary cards carry only name, age, town, date and link (no TL;DR, Riff or cause of death)`);
  ok(o.stars===6&&o.read.split(';').length===6,`${tag} the on-air read is still 6 names (${o.stars} starred, ${o.read.split(';').length} in the read)`);
  await p.click('#obmore'); await delay(200); o=await vis();
  ok(o.vis===tot&&!o.hidden&&o.exp==='true'&&/^Hide the previous week/.test(o.btn),`${tag} tapping the button expands in place: ${o.vis} of ${tot} shown, "${o.btn}"`);
  ok(o.sw<=o.iw,`${tag} no horizontal overflow with all obituaries shown`);
  await p.click('#obmore'); await delay(200); o=await vis(); ok(o.vis===wk&&o.hidden,`${tag} tapping again collapses back to ${o.vis}`);
  // the section badges never clip (the old phone "3 CONFIRM" cut-off)
  await p.evaluate(()=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);scrollTo(0,0)}); await delay(150);
  const clip=await p.evaluate(()=>[...document.querySelectorAll('details.sec>summary')].flatMap(s=>{const sr=s.getBoundingClientRect(),sm=s.querySelector('.sm');const out=[];if(sm&&sm.scrollWidth>sm.clientWidth+1)out.push(s.parentElement.id+' .sm clipped '+sm.scrollWidth+'>'+sm.clientWidth);
    [...s.querySelectorAll('.sm>*')].filter(e=>e.offsetWidth>0).forEach(e=>{const r=e.getBoundingClientRect();if(r.right>sr.right-2||r.left<sr.left)out.push(s.parentElement.id+' '+e.textContent+' outside bar')});return out}));
  ok(clip.length===0,`${tag} no badge or count is clipped on any section bar ${JSON.stringify(clip.slice(0,4))}`);
  // screenshots
  if(w===1024){await p.screenshot({path:SHOTS+'/v3-1024-collapsed.png'})}
  if(w===1440||w===390||w===820){const id=w===820?'blk-J':'blk-C';await p.evaluate((id)=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);const d=document.getElementById(id);d.open=true;scrollTo(0,d.getBoundingClientRect().top+scrollY-(document.getElementById('pin').offsetHeight+6))},id);await delay(400);
    await p.screenshot({path:`${SHOTS}/v3-${w}-${id==='blk-C'?'block-C':'block-J'}-expanded.png`})}
  if(w===1440){for(const id of ['chisme','obits']){await p.evaluate((id)=>{[...document.querySelectorAll('details.sec')].forEach(d=>d.open=false);const d=document.getElementById(id);d.open=true;scrollTo(0,d.getBoundingClientRect().top+scrollY-(document.getElementById('pin').offsetHeight+6))},id);await delay(350);await p.screenshot({path:`${SHOTS}/v3-1440-${id}-expanded.png`})}}
  await p.close();
 }

 // ---------- t53u: pinned A-L timeline with playhead; ?t=<minutes> test hook ----------
 for(const [w,h,ua,tag] of [[1440,900,null,'1440'],[390,844,IPHONE,'390']]){
  for(const tm of [0,23,60]){
   const p=await openHttp(w,h,ua,'?t='+tm); await delay(1600);
   const r=await p.evaluate(()=>{const tl=document.getElementById('tl'),ph=document.getElementById('ph'),br=tl.getBoundingClientRect(),pr=ph.getBoundingClientRect();
     const A=[...tl.querySelectorAll('a')];const cn=document.getElementById('cwnext');
     return {state:tl.dataset.state,pct:parseFloat(ph.dataset.pct),leftPx:(pr.left-br.left-2),w:br.width-4,top:pr.top-br.top,ph:pr.height,bh:br.height,
      done:A.filter(a=>a.classList.contains('done')).map(a=>a.dataset.letter).join(''),live:A.filter(a=>a.classList.contains('live')).map(a=>a.dataset.letter).join(''),
      nextChip:document.getElementById('cwn-c').textContent,nextLabel:document.getElementById('cwn-l').textContent,mini:document.getElementById('mb-next').textContent,sw:document.documentElement.scrollWidth,iw:innerWidth,fit:tl.scrollWidth<=tl.clientWidth+1}});
   const exp=tm/60*100, doneExp={0:'',23:'ABCD',60:'ABCDEFGHIJKL'}[tm];
   ok(Math.abs(r.pct-exp)<0.5&&Math.abs(r.leftPx/r.w*100-exp)<1.2,`${tag} t=${tm}: playhead at ${exp.toFixed(1)}% (data ${r.pct}%, drawn ${(r.leftPx/r.w*100).toFixed(1)}%)`);
   ok(r.ph>=r.bh-4,`${tag} t=${tm}: playhead line spans the full bar height (${Math.round(r.ph)}/${Math.round(r.bh)}px)`);
   ok(r.done===doneExp,`${tag} t=${tm}: covered (darker) segments = "${r.done}" (expected "${doneExp}")`);
   if(tm===23){ok(r.live==='E'&&r.nextChip==='F'&&/^Next:/.test(r.nextLabel),`${tag} t=23: current block E, countdown says next is ${r.nextChip}; consistent with the bar`); ok(/Next:/.test(r.mini),`${tag} t=23: pinned bar mirrors the countdown ("${r.mini}")`);}
   if(tm===0) ok(r.state==='run'&&r.live==='A',`${tag} t=0: show running at the left edge, block A live`);
   if(tm===60) ok(r.state==='post'&&r.live===''&&/over/i.test(r.nextLabel),`${tag} t=60: playhead at the right edge, show over, all covered`);
   ok(r.sw<=r.iw&&r.fit,`${tag} t=${tm}: timeline fits, no horizontal overflow`);
   if(tm===23){
     await p.evaluate(()=>scrollTo(0,1600));await delay(500);
     const pin=await p.evaluate(()=>{const e=document.getElementById('pin').getBoundingClientRect();return {top:e.top,h:e.height,y:scrollY}});
     ok(pin.y>500&&Math.abs(pin.top)<1,`${tag} t=23: timeline stays pinned at the top after scrolling (scrollY ${Math.round(pin.y)}, top ${pin.top}, ${Math.round(pin.h)}px tall)`);
     await p.screenshot({path:`${SHOTS}/v2-${tag}-t23.png`});
     await p.evaluate(()=>scrollTo(0,0));await delay(200);
     await p.evaluate(()=>{document.querySelector('#tl a[data-jump="blk-C"]').click()});await delay(700);
     const jmp=await p.evaluate(()=>({c:document.getElementById('blk-C').open,top:document.getElementById('blk-C').getBoundingClientRect().top}));
     ok(jmp.c&&jmp.top<400,`${tag} tapping segment C opens block C and scrolls to it (top ${Math.round(jmp.top)}px)`);
   }
   await p.close();
  }
 }
 srv.close();
 console.log('FAILS',JSON.stringify(fails));
 console.log('ERRORS',JSON.stringify(errs));
 await b.close();
})();
