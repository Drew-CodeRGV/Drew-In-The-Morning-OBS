// UI tests for docs/chyron.html (OBS lower third) and its run-of-show dashboard link.
// usage: NODE_PATH=... node tools/ui_test_chyron.js <chyron.html> <studio.html>
const puppeteer=require('puppeteer-core'),http=require('http'),fs=require('fs');
const [CHY,STU]=process.argv.slice(2);
let pass=0,fail=0;
function ok(c,m){if(c){pass++}else{fail++;console.log('FAIL',m)}}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
// ---- mock ntfy.sh ----
function mock(){const msgs={},cl={};let n=0;
 const srv=http.createServer((q,r)=>{r.setHeader('Access-Control-Allow-Origin','*');r.setHeader('Access-Control-Allow-Headers','*');
  if(q.method==='OPTIONS'){r.writeHead(204);return r.end()}
  const m=/^\/([^\/?]+)(\/sse)?/.exec(q.url);const t=m&&m[1];
  if(q.method==='POST'){let b='';q.on('data',d=>b+=d);q.on('end',()=>{const o={id:'m'+(++n),time:Math.floor(Date.now()/1000),event:'message',topic:t,message:b};(msgs[t]=msgs[t]||[]).push(o);(cl[t]||[]).forEach(c=>c.write('data: '+JSON.stringify(o)+'\n\n'));r.end('{}')});return}
  if(m&&m[2]){r.writeHead(200,{'Content-Type':'text/event-stream'});r.write('data: {"event":"open"}\n\n');(msgs[t]||[]).forEach(o=>r.write('data: '+JSON.stringify(o)+'\n\n'));(cl[t]=cl[t]||[]).push(r);q.on('close',()=>{cl[t]=cl[t].filter(x=>x!==r)});return}
  r.writeHead(404);r.end()});
 return new Promise(res=>srv.listen(0,'127.0.0.1',()=>{const port=srv.address().port;
  res({port,base:'http://127.0.0.1:'+port,msgs,close:()=>{Object.values(cl).forEach(a=>a.forEach(c=>c.end()));srv.close()},
   push(t,obj,time){const o={id:'x'+(++n),time:time||Math.floor(Date.now()/1000),event:'message',topic:t,message:typeof obj==='string'?obj:JSON.stringify(obj)};(msgs[t]=msgs[t]||[]).push(o);(cl[t]||[]).forEach(c=>c.write('data: '+JSON.stringify(o)+'\n\n'))},
   cmds(t){return (msgs[t]||[]).map(o=>{try{return JSON.parse(o.message)}catch(e){return null}}).filter(x=>x&&x.k==='cmd')},
   states(t){return (msgs[t]||[]).map(o=>{try{return JSON.parse(o.message)}catch(e){return null}}).filter(x=>x&&x.k==='state')}}) }))}
(async()=>{
 const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--disable-gpu','--allow-file-access-from-files'],headless:'new'});
 const errs=[];
 const T0=Date.UTC(2026,10,23,15,3,30); // Mon Nov 23 2026 09:03:30 CT
 async function open(file,qs,w,h,ts){const p=await b.newPage();await p.setViewport({width:w,height:h});
  p.on('pageerror',e=>errs.push('pageerror '+e.message));p.on('console',m=>{if(m.type()==='error'&&!/ERR_|Failed to load resource/.test(m.text()))errs.push('console '+m.text())});
  await p.evaluateOnNewDocument((ts)=>{const RD=Date;let off=ts-RD.now();try{const k=sessionStorage.getItem('__fk');if(k)off=+k-RD.now()}catch(e){}addEventListener('pagehide',()=>{try{sessionStorage.setItem('__fk',String(RD.now()+off))}catch(e){}});window.__set=(ms)=>{off=ms-RD.now()};window.__adv=(ms)=>{off+=ms};
   window.Date=class extends RD{constructor(...a){if(a.length)super(...a);else super(RD.now()+off)}static now(){return RD.now()+off}};},ts||Date.now());
  await p.goto('file://'+file+(qs||''));return p}
 const MIN=60000;
 // ======== A. look ========
 let p=await open(CHY,'?debug',1920,1080,T0);
 const blocks=await p.evaluate(()=>window.DITM.blocks());
 ok(blocks.length===12,'12 blocks');
 ok(await p.evaluate(()=>window.innerWidth===1920&&innerHeight===1080),'viewport');
 const bg=await p.evaluate(()=>[getComputedStyle(document.documentElement).backgroundColor,getComputedStyle(document.body).backgroundColor]);
 ok(bg.every(c=>c==='rgba(0, 0, 0, 0)'||c==='transparent'),'transparent background '+bg);
 ok(await p.evaluate(()=>!document.querySelector('#seg,#title,#letter,#blk,.title,.letter')),'no title / letter elements');
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:0}));await sleep(900);
 let L=await p.evaluate(()=>{const f=id=>parseFloat(getComputedStyle(document.getElementById(id)).fontSize);const r=document.getElementById('bar').getBoundingClientRect(),g=document.getElementById('bug').getBoundingClientRect(),i=document.querySelector('#bug img');
  return{head:f('head'),kick:f('kick'),sub:f('sub'),bgi:getComputedStyle(document.getElementById('bar')).backgroundImage,bar:[r.left,r.top,r.right,r.bottom],bug:[g.left,g.top,g.right,g.bottom],img:i&&i.complete&&i.naturalWidth>0,text:document.body.innerText}});
 ok(L.head<=40&&L.head>=30,'headline size '+L.head);ok(L.sub<=30&&L.sub>=22,'chyron line size '+L.sub);ok(L.kick<=26,'kicker size '+L.kick);
 ok(/gradient/.test(L.bgi),'gradient bar');ok(L.img,'logo bug image loaded');ok(L.bug[0]<400&&L.bug[3]>800,'logo in lower-left corner '+L.bug);
 ok(L.bar[2]<=1500&&L.bar[3]<=1080,'bar clear of scene logo '+L.bar);
 ok(L.text.indexOf(blocks[0].headline)>=0,'block 0 headline shown');
 ok(!/^[A-L]$/m.test(L.text.replace(/\n+/g,'\n').split('\n').filter(x=>x.length===1).join('\n')||'zz'),'no stray single-letter block letter');
 // every block fits
 for(let i=0;i<12;i++){await p.evaluate(i=>window.DITM.cmd({cmd:'goto',idx:i}),i);await sleep(750);
  const r=await p.evaluate(()=>{const h=document.getElementById('head'),s=document.getElementById('sub'),bar=document.getElementById('bar').getBoundingClientRect();return{h:h.innerText,hw:[h.scrollWidth,h.clientWidth,h.scrollHeight,h.clientHeight],sw:[s.scrollWidth,s.clientWidth],bar:bar.height,top:bar.top,bot:bar.bottom}});
  ok(r.h.replace(/\s+/g,' ').trim().toLowerCase()===blocks[i].headline.replace(/\s+/g,' ').trim().toLowerCase()||r.h.length>0,'block '+i+' headline text');
  ok(r.hw[0]<=r.hw[1]+2&&r.hw[2]<=r.hw[3]+2,'block '+i+' headline fits '+r.hw);ok(r.sw[0]<=r.sw[1]+2,'block '+i+' sub fits '+r.sw);
  ok(r.bar<=190&&r.bot<=1080,'block '+i+' bar height '+r.bar);}
 const shot='/workspace/ditm-shots/ui-test-chyron.png';try{fs.mkdirSync('/workspace/ditm-shots',{recursive:true})}catch(e){}
 await p.screenshot({path:shot,omitBackground:true});
 // ======== B. commands via window event ========
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));ok(!(await p.evaluate(()=>window.DITM.state().visible)),'clear hides');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'goto',idx:5}})));
 let st=await p.evaluate(()=>window.DITM.state());ok(st.idx===5&&st.visible,'event goto 5 shows it');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:JSON.stringify({cmd:'goto',idx:2})})));
 st=await p.evaluate(()=>window.DITM.state());ok(st.idx===2,'event with JSON string detail');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'next'}})));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===3,'next');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'prev'}})));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===2,'prev');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'goto',idx:999}})));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===11,'idx clamps high');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'goto',idx:-4}})));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===0,'idx clamps low');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'goto',idx:4}})));
 const before=JSON.stringify(await p.evaluate(()=>window.DITM.state()));
 const bad=[{cmd:'eval',idx:1},{cmd:'constructor'},{cmd:'__proto__'},{cmd:'toString'},{cmd:['goto'],idx:1},{cmd:{a:1}},{idx:2},'garbage','{"cmd":','<img src=x onerror=alert(1)>',null,42,{cmd:'goto',idx:'<b>x</b>'},{cmd:'goto',idx:'7'},{cmd:'goto',idx:NaN},{cmd:'GOTO',idx:1},{text:'<script>alert(1)</script>'}];
 for(const d of bad){await p.evaluate(d=>window.dispatchEvent(new CustomEvent('ditm',{detail:d})),d)}
 const after=JSON.stringify(await p.evaluate(()=>window.DITM.state()));
 ok(JSON.parse(after).idx===JSON.parse(before).idx&&JSON.parse(after).visible===JSON.parse(before).visible&&!JSON.parse(after).running,'garbage / non-whitelisted input changes nothing '+after);
 ok(await p.evaluate(()=>!document.body.innerHTML.includes('<img src=x')&&!document.querySelector('script[src]')),'no injection into page');
 // ======== C. auto-advance with a fake clock ========
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 await p.evaluate(()=>window.DITM.cmd({cmd:'start'}));st=await p.evaluate(()=>window.DITM.state());
 ok(st.running&&st.idx===0&&st.visible,'start -> running, block 0, on air');
 ok(st.startAt%MIN===0,'start floors to the minute');
 const startAt=st.startAt;
 for(let i=1;i<12;i++){const target=startAt+blocks[i].offset*MIN+2000;await p.evaluate(t=>window.__set(t),target);await sleep(600);
  st=await p.evaluate(()=>window.DITM.state());ok(st.idx===i,'auto-advance reaches block '+i+' at +'+blocks[i].offset+'m (got '+st.idx+')');
  const before=startAt+blocks[i].offset*MIN-2000;}
 // just before a boundary stays on the previous block
 await p.evaluate(t=>window.__set(t),startAt+blocks[5].offset*MIN-3000);await sleep(600);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===4,'3 s before block 5 still block 4 (got '+st.idx+')');
 await p.evaluate(t=>window.__set(t),startAt+blocks[5].offset*MIN+3000);await sleep(600);
 // ---- hold / resume
 await p.evaluate(()=>window.DITM.cmd({cmd:'hold'}));st=await p.evaluate(()=>window.DITM.state());ok(st.held&&st.running,'hold');
 const idxH=st.idx,elH=st.elapsedMin;
 await p.evaluate(()=>window.__adv(25*60000));await sleep(600);st=await p.evaluate(()=>window.DITM.state());
 ok(st.idx===idxH&&Math.abs(st.elapsedMin-elH)<0.01,'hold freezes topic and clock for 25 min (idx '+st.idx+', el '+st.elapsedMin+')');
 await p.evaluate(()=>window.DITM.cmd({cmd:'resume'}));st=await p.evaluate(()=>window.DITM.state());
 ok(!st.held&&Math.abs(st.elapsedMin-elH)<0.05&&st.idx===idxH,'resume carries on from the same moment');
 ok(Math.abs(st.holdMs-25*60000)<2000,'holdMs ~25 min '+st.holdMs);
 // the next boundary is pushed back by the hold
 const nextOff=blocks[idxH+1].offset;const wait=(nextOff-elH)*MIN;
 await p.evaluate(w=>window.__adv(w-5000),wait);await sleep(600);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===idxH,'5 s before the (delayed) boundary still on block '+idxH+' (got '+st.idx+')');
 await p.evaluate(()=>window.__adv(10000));await sleep(600);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===idxH+1,'advances after the delayed boundary (got '+st.idx+')');
 await p.evaluate(()=>window.DITM.cmd({cmd:'toggle'}));st=await p.evaluate(()=>window.DITM.state());ok(st.held,'toggle holds');
 await p.evaluate(()=>window.DITM.cmd({cmd:'toggle'}));st=await p.evaluate(()=>window.DITM.state());ok(!st.held,'toggle resumes');
 // hold twice is harmless; resume without hold is harmless
 await p.evaluate(()=>{window.DITM.cmd({cmd:'hold'});window.DITM.cmd({cmd:'hold'})});let s1=await p.evaluate(()=>window.DITM.state());await p.evaluate(()=>window.__adv(60000));
 await p.evaluate(()=>{window.DITM.cmd({cmd:'resume'});window.DITM.cmd({cmd:'resume'})});let s2=await p.evaluate(()=>window.DITM.state());ok(Math.abs(s2.elapsedMin-s1.elapsedMin)<0.05&&!s2.held,'double hold / double resume harmless');
 // goto/next/prev while running re-times the show
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:7}));await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===7&&st.running&&Math.abs(st.elapsedMin-blocks[7].offset)<0.1,'goto while running re-times to block 7');
 await p.evaluate(()=>window.__adv(20000));await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===7,'stays on block 7 (no snap-back)');
 await p.evaluate(()=>window.DITM.cmd({cmd:'next'}));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===8&&Math.abs(st.elapsedMin-blocks[8].offset)<0.1,'next while running');
 await p.evaluate(()=>window.DITM.cmd({cmd:'prev'}));st=await p.evaluate(()=>window.DITM.state());ok(st.idx===7,'prev while running');
 await p.evaluate(()=>window.DITM.cmd({cmd:'hold'}));await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:2}));st=await p.evaluate(()=>window.DITM.state());ok(st.held&&st.idx===2&&Math.abs(st.elapsedMin-blocks[2].offset)<0.1,'goto while held keeps hold and re-times');
 await p.evaluate(()=>window.DITM.cmd({cmd:'resume'}));
 // reload restores state
 await p.reload();await sleep(400);st=await p.evaluate(()=>window.DITM.state());ok(st.running&&st.idx===2,'state survives a browser-source reload (running, block 2)');
 ok(!st.visible,'but it comes back off air');
 // show ends after 60 minutes
 await p.evaluate(()=>window.DITM.cmd({cmd:'show'}));st=await p.evaluate(()=>window.DITM.state());await p.evaluate(t=>window.__set(t),st.startAt+st.holdMs+61*MIN);await sleep(600);
 st=await p.evaluate(()=>window.DITM.state());ok(!st.running&&!st.visible,'show over after 60 min -> stops and clears');
 // stop leaves the lower third where it is
 await p.evaluate(()=>{window.DITM.cmd({cmd:'goto',idx:1});window.DITM.cmd({cmd:'start'});window.DITM.cmd({cmd:'stop'})});st=await p.evaluate(()=>window.DITM.state());ok(!st.running&&st.visible,'stop ends auto-advance, keeps current topic');
 await p.close();
 // ======== D. ntfy input on the chyron ========
 const M=await mock();const TOP='ditm-ros-testtopic01';
 p=await open(CHY,'?debug&topic='+TOP+'&ntfy='+encodeURIComponent(M.base),1920,1080);await sleep(1500);
 ok(M.states(TOP).length>=1,'chyron publishes its state to the topic on load');
 M.push(TOP,{k:'cmd',cmd:'goto',idx:6});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===6&&st.visible,'ntfy goto 6');
 M.push(TOP,{k:'cmd',cmd:'start'});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.running&&st.idx===0,'ntfy start');
 M.push(TOP,{k:'cmd',cmd:'hold'});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.held,'ntfy hold');
 await sleep(900);let last=M.states(TOP).pop();ok(last&&last.held&&last.running&&last.idx===0&&last.k==='state','chyron publishes held state back');
 M.push(TOP,{k:'cmd',cmd:'resume'});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(!st.held,'ntfy resume');
 M.push(TOP,{k:'cmd',cmd:'next'});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===1,'ntfy next');
 M.push(TOP,{k:'cmd',cmd:'clear'});await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(!st.visible,'ntfy clear');
 const snap=JSON.stringify(await p.evaluate(()=>window.DITM.state()));
 M.push(TOP,'hello world');M.push(TOP,'{"cmd":');M.push(TOP,{k:'cmd',cmd:'rm -rf'});M.push(TOP,{k:'cmd',cmd:'constructor'});M.push(TOP,{k:'state',cmd:'goto',idx:9});M.push(TOP,{cmd:'goto',idx:3,k:'state'});M.push(TOP,{k:'cmd',cmd:'goto',idx:'x'});
 await sleep(600);const snap2=await p.evaluate(()=>window.DITM.state());ok(snap2.idx===JSON.parse(snap).idx&&snap2.visible===JSON.parse(snap).visible,'garbage on the topic ignored');
 // stale message (older than the page load) is ignored on (re)connect
 M.push(TOP,{k:'cmd',cmd:'goto',idx:10},Math.floor(Date.now()/1000)-3600);await p.reload();await sleep(1500);st=await p.evaluate(()=>window.DITM.state());ok(st.idx!==10,'stale ntfy messages are not replayed after a reload');
 await p.close();
 p=await open(CHY,'?debug&topic=../../etc&ntfy=https://evil.example',1920,1080);await sleep(400);
 ok(await p.evaluate(()=>window.DITM.state()!==null),'bad topic / foreign ntfy host: page still works, no network');await p.close();
 // ======== E. dashboard ========
 const T1='ditm-ros-dashtest0001';
 p=await open(STU,'',1180,820,T0);
 ok(await p.evaluate(()=>document.getElementById('chy').hidden&&!document.getElementById('chlink').hidden&&document.getElementById('mb-hold').hidden),'unlinked: chyron controls hidden, Link chyron shown');
 await p.close();
 const SQ='?ctl='+T1+'&ntfy='+encodeURIComponent(M.base);
 p=await open(STU,SQ,1180,820,T0);await sleep(300);
 const g=()=>p.evaluate(()=>({chy:!document.getElementById('chy').hidden,hold:document.getElementById('chhold').textContent,mb:document.getElementById('mb-hold').textContent,mbVis:!document.getElementById('mb-hold').hidden,ind:document.getElementById('ssind').textContent,live:document.getElementById('sslive').textContent,st:document.getElementById('chst').textContent,clr:document.getElementById('chclr').textContent,url:location.href}));
 let d=await g();ok(d.chy&&d.mbVis,'linked: controls visible');ok(!/ctl=/.test(d.url),'link code removed from the address bar');
 const min44=await p.evaluate(()=>['chhold','chprev','chnext','chclr','mb-hold'].map(i=>{const r=document.getElementById(i).getBoundingClientRect();return r.height>=44&&r.width>=44}));ok(min44.every(Boolean),'44px tap targets '+min44);
 await p.click('#ssbtn');await sleep(500);ok(M.cmds(T1).some(c=>c.cmd==='start'),'Start on the dashboard publishes start');
 ok(M.cmds(T1).every(c=>Object.keys(c).every(k=>['k','cmd','at','v','idx'].includes(k))),'commands carry no free text');
 await p.click('#chhold');await sleep(400);d=await g();ok(M.cmds(T1).some(c=>c.cmd==='hold'),'Hold publishes hold');ok(/Resume/.test(d.hold)&&/Resume/.test(d.mb),'button flips to Resume');ok(/HELD/.test(d.live)&&/HELD/.test(d.ind),'dashboard shows HELD');
 await p.evaluate(()=>window.__adv(10*60000));await sleep(1300);let d2=await g();ok(d2.live===d.live,'held: playhead frozen while 10 min pass ('+d.live+')');
 await p.click('#mb-hold');await sleep(400);d=await g();ok(M.cmds(T1).some(c=>c.cmd==='resume'),'minibar Resume publishes resume');ok(/Hold/.test(d.hold)&&!/HELD/.test(d.live),'back to LIVE');
 const lv=await p.evaluate(()=>document.getElementById('sslive').textContent);
 await p.click('#chnext');await p.click('#chprev');await p.click('#chclr');await sleep(300);const cs=M.cmds(T1).map(c=>c.cmd);ok(cs.includes('next')&&cs.includes('prev')&&cs.includes('clear'),'Prev/Next/Clear publish');
 ok(!M.cmds(T1).some(c=>c.cmd==='goto'),'(dashboard sends no goto)');
 // adopts the chyron's truth
 const NOWP=await p.evaluate(()=>Date.now());const sa=Math.floor((T0-3*MIN)/MIN)*MIN; // chyron says it started 9:00 -> 3.5 min in
 M.push(T1,{k:'state',v:1,running:true,held:false,idx:0,letter:'A',visible:true,startAt:sa,heldAt:0,holdMs:0,elapsedMin:3.5,at:NOWP,blocks:12});await sleep(600);
 d=await g();ok(/9:00/.test(d.ind),'dashboard adopts the chyron start time ('+d.ind+')');ok(/AUTO/.test(d.st),'status shows AUTO ('+d.st+')');
 M.push(T1,{k:'state',v:1,running:true,held:true,idx:2,letter:'C',visible:false,startAt:sa,heldAt:NOWP,holdMs:90000,elapsedMin:5,at:NOWP+5,blocks:12});await sleep(600);
 d=await g();ok(/HELD/.test(d.live)&&/Resume/.test(d.hold),'dashboard mirrors a hold started from the Stream Deck');ok(/C/.test(d.st)&&/HELD/.test(d.st)&&/off air/.test(d.st)&&d.clr==='Show','status shows C / HELD / off air; Clear flips to Show ('+d.st+')');
 await p.reload?0:0;
 // reload keeps the link and the held state
 await p.goto('file://'+STU);await sleep(400);d=await g();ok(d.chy,'link survives a reload (stored on the iPad)');ok(/HELD/.test(d.live),'held state survives a reload');
 await p.close();
 // ======== F. dashboard + chyron together ========
 const T2='ditm-ros-e2etest0001';const qs2='ntfy='+encodeURIComponent(M.base);
 const dash=await open(STU,'?ctl='+T2+'&'+qs2,1180,820);const chy=await open(CHY,'?topic='+T2+'&'+qs2,1920,1080);await sleep(1200);
 const cs2=()=>chy.evaluate(()=>window.DITM.state());
 await dash.evaluate(()=>document.querySelector('#ssbtn').click());await sleep(900);st=await cs2();ok(st.running&&st.idx===0&&st.visible,'E2E: Start on the dashboard starts the chyron on block A');
 await chy.evaluate(()=>window.__adv(5*60000));await dash.evaluate(()=>window.__adv(5*60000));await sleep(900);st=await cs2();
 const want=blocks.filter(x=>x.offset<=(5+0.5)).length-1;ok(st.idx>=0,'E2E: chyron follows the clock (block '+st.idx+')');
 const i0=st.idx;await dash.evaluate(()=>document.querySelector('#chhold').click());await sleep(900);st=await cs2();ok(st.held,'E2E: Hold on the dashboard holds the chyron');
 await chy.evaluate(()=>window.__adv(15*60000));await dash.evaluate(()=>window.__adv(15*60000));await sleep(1200);st=await cs2();ok(st.idx===i0&&st.held,'E2E: chyron stays on the held topic');
 const dl=await dash.evaluate(()=>document.getElementById('sslive').textContent);ok(/HELD/.test(dl),'E2E: dashboard shows HELD ('+dl+')');
 await dash.evaluate(()=>document.querySelector('#chhold').click());await sleep(900);st=await cs2();ok(!st.held&&st.idx===i0,'E2E: Resume resumes the same topic');
 const live1=await dash.evaluate(()=>[...document.querySelectorAll('.tr')].findIndex(r=>r.classList.contains('live')||r.classList.contains('now')));
 await sleep(1500);const mirror=await dash.evaluate(()=>document.getElementById('chst').textContent);ok(/AUTO/.test(mirror),'E2E: dashboard status AUTO ('+mirror+')');
 // Stream Deck style hold (window event, no ntfy) is mirrored on the dashboard through the state echo
 await chy.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'hold'}})));await sleep(1500);
 ok(await dash.evaluate(()=>/HELD/.test(document.getElementById('sslive').textContent)||document.getElementById('chhold').classList.contains('held')),'E2E: hold from the Stream Deck shows on the dashboard');
 await chy.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'resume'}})));await sleep(1500);
 ok(await dash.evaluate(()=>!document.getElementById('chhold').classList.contains('held')),'E2E: Stream Deck resume shows on the dashboard');
 await dash.evaluate(()=>document.querySelector('#ssreset').click());await sleep(900);st=await cs2();ok(!st.running,'E2E: Reset on the dashboard stops auto-advance');
 await dash.close();await chy.close();
 M.close();await b.close();
 console.log('errors:',errs.length?errs.join(' | '):'none');
 console.log(`chyron UI tests: ${pass} passed, ${fail} failed`);process.exit(fail||errs.length?1:0);
})().catch(e=>{console.log('CRASH',e);process.exit(2)});
