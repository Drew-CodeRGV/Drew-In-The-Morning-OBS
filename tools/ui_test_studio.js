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
 async function openHttp(w,h,ua){
  const p=await b.newPage(); await p.setViewport({width:w,height:h,deviceScaleFactor:2,isMobile:!!ua,hasTouch:!!ua}); if(ua)await p.setUserAgent(ua);
  p.on('pageerror',e=>errs.push('pageerror '+e.message)); p.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text()))errs.push('console '+m.text())});
  await p.goto(base+rel,{waitUntil:'load'}); return p;
 }
 const st=(p)=>p.evaluate(()=>{const d=[...document.querySelectorAll('details')];const secs=[...document.querySelectorAll('details.sec')];return {total:d.length,open:d.filter(x=>x.open).length,secs:secs.length,secOpen:secs.filter(x=>x.open).length,
   sw:document.documentElement.scrollWidth,iw:innerWidth,minHdr:Math.min(...secs.map(x=>x.querySelector('summary').getBoundingClientRect().height)),
   hdrVisible:secs.every(x=>x.querySelector('summary').getBoundingClientRect().width>100),
   clockVisible:!!document.getElementById('cwnext')&&document.getElementById('cwnext').offsetHeight>0,ssbtn:!!document.getElementById('ssbtn')&&document.getElementById('ssbtn').offsetHeight>0,
   brkVisible:document.getElementById('brk').offsetHeight>0}});
 const fails=[]; const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m); if(!c)fails.push(m)};
 {
  const p0=await openHttp(1180,820,IPAD);
  const t=await p0.evaluate(()=>{const e=document.getElementById('tech');return e?{open:e.open,items:e.querySelectorAll('.item.tech').length,links:[...e.querySelectorAll('.item.tech a[href^="http"]')].length,badge:(e.querySelector('summary').textContent||'').includes('TECH'),nav:!!document.querySelector('nav a[href="#tech"]'),hdr:e.querySelector('summary').getBoundingClientRect().height}:null});
  ok(!!t,'Tech section exists'); if(t){ ok(!t.open,'Tech section starts collapsed'); ok(t.items>=3&&t.items<=5,'Tech section has 3-5 items ('+t.items+')'); ok(t.links>=t.items,'every Tech item links to its article'); ok(t.badge&&t.nav&&t.hdr>=44,'Tech header badge, nav link and 44px+ target'); }
  const jr=await p0.evaluate(()=>{const j=document.getElementById('blk-J');return j?j.textContent.includes('TECH SUB-SEGMENT')&&j.textContent.includes('quick tech check'):false});
  ok(jr,'Block J (rundown) carries the Tech sub-segment and its segue');
  const ob=await p0.evaluate(()=>{const e=document.getElementById('obits');if(!e)return null;const L=document.getElementById('blk-L');return {open:e.open,links:[...e.querySelectorAll('.obl a[href^="https://www.legacy.com/"]')].length,lis:e.querySelectorAll('.obl li').length,groups:e.querySelectorAll('.obh').length,nav:!!document.querySelector('nav a[href="#obits"]'),hdr:e.querySelector('summary').getBoundingClientRect().height,script:!!e.querySelector('#obscript'),lread:L?L.textContent.includes('READ ALOUD, SLOWLY')||L.textContent.includes('REMEMBERING OUR NEIGHBORS'):false,cause:/cancer|cause of death/i.test(e.textContent)}});
  ok(!!ob,'Remembering Our Neighbors section exists'); if(ob){ ok(!ob.open,'Neighbors section starts collapsed'); ok(ob.lis>0&&ob.links===ob.lis,'every neighbor name links to its Legacy obituary ('+ob.links+'/'+ob.lis+')'); ok(ob.groups>=1,'grouped by week ('+ob.groups+' groups)'); ok(ob.nav&&ob.hdr>=44&&ob.script,'Neighbors nav link, 44px+ header and on-air read'); ok(ob.lread,'Block L carries the obituary read'); ok(!ob.cause,'no cause of death text'); }
  const ut=await p0.evaluate(()=>{const e=document.getElementById('upto');if(!e)return null;return {open:e.open,text:e.textContent,script:(document.getElementById('uptotext')||{}).textContent||''}});
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
  const rdOpen=await p.evaluate(()=>{const e=document.getElementById('rundown'),c=document.getElementById('blk-C');return [e&&e.open,c&&c.open]}); console.log('rundown/block C open after reload',JSON.stringify(rdOpen));
  const pg=await b.newPage(); await pg.setViewport({width:1180,height:820}); await pg.goto(base+rel,{waitUntil:'load'});
  ok(await pg.evaluate(()=>[...document.querySelectorAll('details')].every(d=>!d.open)),'fresh tab/session starts fully collapsed'); await pg.close();
  // jump link from nav opens its section
  await p.evaluate(()=>{[...document.querySelectorAll('details')].forEach(d=>d.open=false)});
  const nav=await p.evaluate(()=>[...document.querySelectorAll('nav a')].map(a=>a.getAttribute('href')+'|'+a.textContent).slice(0,3)); console.log('nav',JSON.stringify(nav));
  // sort toggle
  const firstTitles=()=>p.evaluate(()=>[...document.querySelectorAll('#national .sortbox > details')].map(d=>d.dataset.sc+'/'+d.dataset.ord));
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
 srv.close();
 console.log('FAILS',JSON.stringify(fails));
 console.log('ERRORS',JSON.stringify(errs));
 await b.close();
})();
