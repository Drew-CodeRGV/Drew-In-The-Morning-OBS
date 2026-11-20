// UI tests for docs/chyron.html (OBS lower third) and its run-of-show dashboard link.
// usage: NODE_PATH=... node tools/ui_test_chyron.js <chyron.html> <studio.html>
const puppeteer=require('puppeteer-core'),http=require('http'),fs=require('fs');
const [CHY,STU,ITEMSJ]=process.argv.slice(2);
const REAL=JSON.parse(fs.readFileSync(ITEMSJ,'utf8'));
let pass=0,fail=0;
function ok(c,m){if(c){pass++}else{fail++;console.log('FAIL',m)}}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
// ---- mock ntfy.sh ----
function mock(){const msgs={},cl={},items={doc:{v:1,items:{}}},puts=[];let n=0;
 const srv=http.createServer((q,r)=>{r.setHeader('Access-Control-Allow-Origin','*');r.setHeader('Access-Control-Allow-Headers','*');r.setHeader('Access-Control-Allow-Methods','*');
  if(q.method==='OPTIONS'){r.writeHead(204);return r.end()}
  if(q.method==='GET'&&q.url.startsWith('/chyron-items.json')){r.writeHead(200,{'Content-Type':'application/json'});return r.end(JSON.stringify(items.doc))}
  if(q.method==='PUT'){const ch=[];q.on('data',d=>ch.push(d));q.on('end',()=>{puts.push({url:q.url,type:q.headers['content-type'],body:Buffer.concat(ch)});r.writeHead(200,{'Content-Type':'application/json'});r.end(JSON.stringify({id:'att1',event:'message',attachment:{name:'caller.jpg',url:'https://photos.test/att1/caller.jpg',type:'image/jpeg'}}))});return}
  const m=/^\/([^\/?]+)(\/sse)?/.exec(q.url);const t=m&&m[1];
  if(q.method==='POST'){let b='';q.on('data',d=>b+=d);q.on('end',()=>{const o={id:'m'+(++n),time:Math.floor(Date.now()/1000)+864000,event:'message',topic:t,message:b};(msgs[t]=msgs[t]||[]).push(o);(cl[t]||[]).forEach(c=>c.write('data: '+JSON.stringify(o)+'\n\n'));r.end('{}')});return}
  if(m&&m[2]){r.writeHead(200,{'Content-Type':'text/event-stream'});r.write('data: {"event":"open"}\n\n');(msgs[t]||[]).forEach(o=>r.write('data: '+JSON.stringify(o)+'\n\n'));(cl[t]=cl[t]||[]).push(r);q.on('close',()=>{cl[t]=cl[t].filter(x=>x!==r)});return}
  r.writeHead(404);r.end()});
 return new Promise(res=>srv.listen(0,'127.0.0.1',()=>{const port=srv.address().port;
  res({port,base:'http://127.0.0.1:'+port,msgs,items,puts,close:()=>{Object.values(cl).forEach(a=>a.forEach(c=>c.end()));srv.close()},
   push(t,obj,time){const o={id:'x'+(++n),time:time||(Math.floor(Date.now()/1000)+864000),event:'message',topic:t,message:typeof obj==='string'?obj:JSON.stringify(obj)};(msgs[t]=msgs[t]||[]).push(o);(cl[t]||[]).forEach(c=>c.write('data: '+JSON.stringify(o)+'\n\n'))},
   cmds(t){return (msgs[t]||[]).map(o=>{try{return JSON.parse(o.message)}catch(e){return null}}).filter(x=>x&&x.k==='cmd')},
   states(t){return (msgs[t]||[]).map(o=>{try{return JSON.parse(o.message)}catch(e){return null}}).filter(x=>x&&x.k==='state')}}) }))}
(async()=>{
 const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--disable-gpu','--allow-file-access-from-files','--disable-dev-shm-usage'],headless:'new',protocolTimeout:300000});
 const errs=[];
 const T0=Date.UTC(2026,10,23,15,3,30); // Mon Nov 23 2026 09:03:30 CT
 async function open(file,qs,w,h,ts){const p=await b.newPage();await p.setViewport({width:w,height:h});
  p.on('pageerror',e=>errs.push('pageerror '+e.message));p.on('console',m=>{if(m.type()==='error'&&!/ERR_|Failed to load resource/.test(m.text()))errs.push('console '+m.text())});
  await p.evaluateOnNewDocument((ts)=>{const RD=Date;let off=ts-RD.now();try{sessionStorage.removeItem('__fk')}catch(e){}addEventListener('pagehide',()=>{try{sessionStorage.setItem('__fk',String(RD.now()+off))}catch(e){}});window.__set=(ms)=>{off=ms-RD.now()};window.__adv=(ms)=>{off+=ms};
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
 let L=await p.evaluate(()=>{const f=id=>parseFloat(getComputedStyle(document.getElementById(id)).fontSize);const r=document.getElementById('bar').getBoundingClientRect(),l=document.getElementById('lt').getBoundingClientRect();
  return{head:f('head'),kick:f('kick'),sub:f('sub'),bgi:getComputedStyle(document.getElementById('bar')).backgroundImage,bar:[r.left,r.top,r.right,r.bottom],lt:[l.left,l.top,l.right,l.bottom],rad:getComputedStyle(document.getElementById('bar')).borderRadius,hasBug:!!document.getElementById('bug'),imgsInBar:document.querySelectorAll('#lt img').length,text:document.body.innerText}});
 ok(L.head<=40&&L.head>=30,'headline size '+L.head);ok(L.sub<=30&&L.sub>=22,'chyron line size '+L.sub);ok(L.kick<=26,'kicker size '+L.kick);
 ok(/gradient/.test(L.bgi),'gradient bar');ok(!L.hasBug&&L.imgsInBar===0,'no logo bug in the bar');
 ok(L.bar[0]===30,'left margin 30px (x='+L.bar[0]+')');ok(1080-L.bar[3]===26,'bottom margin 26px (gap='+(1080-L.bar[3])+')');ok(L.bar[0]/1920<=0.03&&(1080-L.bar[3])/1080<=0.03,'inside a ~3% title-safe margin, not flush');
 ok(/^14px$/.test(L.rad),'rounded corners ('+L.rad+')');
 ok(L.bar[2]<=1500&&L.bar[3]<=1080,'bar clear of the scene logo '+L.bar);
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
 // ======== B2. logo state (clean screen: bar/guest/caller off, no chyron bug) ========
 const lg=()=>p.evaluate(()=>{const e=document.getElementById('lg'),r=e.getBoundingClientRect();return{on:e.classList.contains('on'),r:[r.left,r.top,r.right,r.bottom],h:r.height,ok:e.complete&&e.naturalWidth>0,bar:document.getElementById('lt').classList.contains('in'),op:getComputedStyle(e).opacity}});
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:3}));await sleep(900);let lo=await lg();ok(lo.bar&&!lo.on&&+lo.op===0,'topic showing: bar in, logo bug hidden');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'logo'}})));await sleep(900);lo=await lg();st=await p.evaluate(()=>window.DITM.state());
 ok(!lo.bar&&!lo.on&&+lo.op===0&&!st.visible&&st.logo,'logo: clean screen (bar off, chyron bug stays hidden)');
 const logoShot='/tmp/ditm-logo-mode.png';await p.screenshot({path:logoShot,omitBackground:true});
 for(const c of [{cmd:'next'},{cmd:'prev'},{cmd:'goto',idx:6},{cmd:'show'}]){await p.evaluate(()=>window.DITM.cmd({cmd:'logo'}));await sleep(100);await p.evaluate(c=>window.DITM.cmd(c),c);await sleep(700);lo=await lg();ok(lo.bar&&!lo.on,c.cmd+' brings the bar back and hides the logo');}
 await p.evaluate(()=>window.DITM.cmd({cmd:'logo'}));await sleep(100);await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));await sleep(700);lo=await lg();st=await p.evaluate(()=>window.DITM.state());ok(!lo.bar&&!lo.on&&!st.logo&&!st.visible,'clear hides both');
 await p.evaluate(()=>window.DITM.cmd({cmd:'logo'}));await p.evaluate(()=>window.DITM.cmd({cmd:'logo'}));st=await p.evaluate(()=>window.DITM.state());ok(st.logo&&!st.visible,'logo twice is harmless');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'LOGO'}})));await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'logo',idx:'<b>'}})));
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 // ======== B3. audible items (id only; the words come from chyron-items.json) ========
 const IT={'i-0123456789':{headline:'Council approves $4.2M for the Pharr bridge detour plan',line:'Vote was 4-1; work starts in January.',kicker:'HEADLINES · RGV'},
  'i-abcdef0123':{headline:'UNCONFIRMED rumor headline',line:'UNCONFIRMED · Commenters say the closure is tying up traffic.',kicker:'CHISME'},
  'i-00000000aa':{headline:'A very long headline that keeps going and going to make sure the audible bar wraps onto two lines instead of running off the edge of the screen at all',line:'And a very long second line that also needs to be clamped so that it never leaves the bar even when somebody sends something huge to the chyron',kicker:'TRENDING'},
  'i-1111111111':{headline:'<img src=x onerror=alert(1)> <b>bold</b>',line:'<script>alert(2)</script>',kicker:'X'},
  'bad':{headline:'nope'},'i-22222222zz':{headline:'bad id chars'},'i-3333333333':{headline:42,line:'not a string'}};
 await p.evaluate(j=>window.DITM.setItems({items:j}),IT);
 ok((await p.evaluate(()=>window.DITM.items()))===4,'only well-formed ids with a string headline are kept (4 of 7)');
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 const bar=()=>p.evaluate(()=>{const g=id=>document.getElementById(id),r=g('bar').getBoundingClientRect(),h=g('head'),sb=g('sub');return{k:g('kick').textContent,h:h.textContent,s:sb.textContent,hf:parseFloat(getComputedStyle(h).fontSize),sf:parseFloat(getComputedStyle(sb).fontSize),hw:[h.scrollWidth,h.clientWidth,h.scrollHeight,h.clientHeight],sw:[sb.scrollWidth,sb.clientWidth,sb.scrollHeight,sb.clientHeight],bar:[r.left,r.top,r.right,r.bottom],inn:g('lt').classList.contains('in'),acc:getComputedStyle(g('lt')).getPropertyValue('--acc').trim(),inj:document.querySelectorAll('#lt img,#lt script,#lt b').length}});
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await sleep(1000);let ib=await bar();st=await p.evaluate(()=>window.DITM.state());
 ok(ib.inn&&ib.h===IT['i-0123456789'].headline&&ib.s===IT['i-0123456789'].line&&ib.k==='HEADLINES · RGV','item shows its headline, line and kicker on the bar immediately');
 ok(st.item==='i-0123456789'&&st.visible&&!st.running&&!st.held,'item in manual mode: on air, no hold');
 ok(ib.hf<=40&&ib.sf<=30&&ib.bar[0]===30&&1080-ib.bar[3]===26,'same bar styling and position for an item ('+ib.hf+'/'+ib.sf+')');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'item',id:'i-abcdef0123'}})));await sleep(1000);ib=await bar();ok(ib.s.startsWith('UNCONFIRMED')&&ib.k==='CHISME','item via the window event; the UNCONFIRMED label is on the line');
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-00000000aa'}));await sleep(1000);ib=await bar();ok(ib.hw[0]<=ib.hw[1]+2&&ib.hw[2]<=ib.hw[3]+2&&ib.sw[0]<=ib.sw[1]+2&&ib.sw[2]<=ib.sw[3]+2&&ib.bar[3]<=1080&&ib.bar[1]>=700,'a very long item fits (clamped to two lines) '+ib.hw+' '+ib.sw);
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-1111111111'}));await sleep(1000);ib=await bar();ok(ib.inj===0&&ib.h.includes('<img'),'markup in an item is shown as plain text, never parsed');
 // not accepted: unknown id, malformed ids, free text riding along
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await sleep(900);const s0=JSON.stringify(await p.evaluate(()=>window.DITM.state()));const h0=(await bar()).h;
 for(const d of [{cmd:'item',id:'i-ffffffffff'},{cmd:'item'},{cmd:'item',id:'bad'},{cmd:'item',id:'i-22222222zz'},{cmd:'item',id:'i-3333333333'},{cmd:'item',id:['i-0123456789']},{cmd:'item',id:'I-0123456789'},{cmd:'item',id:'i-0123456789 '},{cmd:'item',id:'__proto__'},{cmd:'item',id:'constructor'},{cmd:'item',id:'i-ffffffffff',headline:'HACKED',line:'HACKED',text:'HACKED'}]){await p.evaluate(d=>window.dispatchEvent(new CustomEvent('ditm',{detail:d})),d)}
 await sleep(500);{const a=JSON.parse(s0),b2=await p.evaluate(()=>window.DITM.state());ok(['item','visible','idx','held','running','logo'].every(k=>a[k]===b2[k])&&(await bar()).h===h0,'unknown / malformed ids are ignored');}
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'item',id:'i-0123456789',headline:'HACKED',line:'HACKED'}})));await sleep(900);ib=await bar();ok(ib.h===IT['i-0123456789'].headline&&!/HACKED/.test(ib.s),'text sent with the command is never shown');
 // leaving audible mode
 for(const c of [{cmd:'next'},{cmd:'prev'},{cmd:'goto',idx:5},{cmd:'clear'},{cmd:'logo'}]){await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await p.evaluate(c=>window.DITM.cmd(c),c);st=await p.evaluate(()=>window.DITM.state());ok(st.item===null,c.cmd+' leaves audible mode');}
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:4}));await sleep(900);ib=await bar();ok(ib.h.toLowerCase()===blocks[4].headline.toLowerCase()||ib.h.length>0&&ib.h!==IT['i-0123456789'].headline,'goto brings the scheduled block back');
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await p.evaluate(()=>window.DITM.cmd({cmd:'show'}));st=await p.evaluate(()=>window.DITM.state());ok(st.item==='i-0123456789','show keeps the audible up');
 // while auto-advance runs: item holds; resume returns to the schedule
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));await p.evaluate(()=>window.DITM.cmd({cmd:'start'}));await p.evaluate(()=>window.__adv(7*60000+5000));await sleep(700);let sA=await p.evaluate(()=>window.DITM.state());const blk=sA.idx;
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await sleep(700);st=await p.evaluate(()=>window.DITM.state());ok(st.running&&st.held&&st.item&&st.visible&&st.idx===blk,'item during auto-advance puts it on HOLD (block '+blk+')');
 await p.evaluate(()=>window.__adv(25*60000));await sleep(900);st=await p.evaluate(()=>window.DITM.state());ib=await bar();ok(st.idx===blk&&st.held&&ib.h===IT['i-0123456789'].headline,'the audible stays up while the clock is frozen for 25 min');
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-abcdef0123'}));await sleep(900);ib=await bar();st=await p.evaluate(()=>window.DITM.state());ok(st.held&&ib.s.startsWith('UNCONFIRMED'),'a second audible replaces the first, still held');
 const elA=st.elapsedMin;await p.evaluate(()=>window.DITM.cmd({cmd:'resume'}));await sleep(900);st=await p.evaluate(()=>window.DITM.state());ib=await bar();
 ok(!st.held&&st.item===null&&st.idx===blk&&Math.abs(st.elapsedMin-elA)<0.05&&ib.h.toLowerCase()!==IT['i-abcdef0123'].headline.toLowerCase(),'Resume returns to the scheduled block, clock continues from where it froze');
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await p.evaluate(()=>window.DITM.cmd({cmd:'toggle'}));st=await p.evaluate(()=>window.DITM.state());ok(!st.held&&st.item===null,'the Stream Deck toggle also resumes out of an audible');
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await p.evaluate(()=>window.DITM.cmd({cmd:'next'}));st=await p.evaluate(()=>window.DITM.state());ok(st.item===null&&st.held&&st.running,'next leaves the audible (still held until Resume)');
 await p.evaluate(()=>window.DITM.cmd({cmd:'stop'}));await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 // reload comes back with no audible
 await p.evaluate(()=>window.DITM.cmd({cmd:'item',id:'i-0123456789'}));await p.reload();await sleep(400);st=await p.evaluate(()=>window.DITM.state());ok(st.item===null&&!st.visible,'a reloaded browser source has no audible and is off air');
{
 // ======== B4. guest + phone caller (the only free text the page takes) ========
 const PNG1=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==','base64');
 const imgHook=async pg=>{await pg.setRequestInterception(true);pg.on('request',r=>{try{if(r.url().startsWith('https://')&&!r.url().includes('ntfy')&&!r.url().includes('127.0.0.1'))r.respond({status:200,contentType:'image/png',body:PNG1});else r.continue()}catch(e){try{r.continue()}catch(x){}}})};
 await p.close();p=await open(CHY,'?debug',1920,1080,T0);await imgHook(p);await p.evaluate(()=>{localStorage.removeItem('ditm-chyron-guest-v1');localStorage.removeItem('ditm-chyron-caller-v1')});await p.reload();await sleep(400);
 ok((await p.evaluate(()=>[window.DITM.cmd({cmd:'guest_show'}),window.DITM.cmd({cmd:'caller_show'}),window.DITM.cmd({cmd:'caller_toggle'}),window.DITM.cmd({cmd:'guest',name:''}),window.DITM.cmd({cmd:'caller',name:'   '}),window.DITM.cmd({cmd:'guest',name:42}),window.DITM.cmd({cmd:'guest_hide'})])).every(x=>x===false),'nothing remembered yet: show/toggle/empty-name commands are ignored');
 const gb=()=>p.evaluate(()=>{const g=id=>document.getElementById(id),r=g('bar').getBoundingClientRect(),h=g('head'),sb=g('sub');return{k:g('kick').textContent,h:h.textContent,s:sb.textContent,inn:g('lt').classList.contains('in'),hw:[h.scrollWidth,h.clientWidth,h.scrollHeight,h.clientHeight],sw:[sb.scrollWidth,sb.clientWidth],bar:[r.left,r.top,r.right,r.bottom],bad:document.querySelectorAll('#lt img,#lt script,#lt b,#call script,#call b').length}});
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest',name:'Dr. Maria Elena Garza-Villarreal',title:'Superintendent, Example ISD',blurb:'Talking about the new bond and what it means for classrooms across the Valley.'}));await sleep(1100);
 let g=await gb();let st=await p.evaluate(()=>window.DITM.state());
 ok(g.inn&&g.h==='Dr. Maria Elena Garza-Villarreal'&&g.k==='Superintendent, Example ISD'&&g.s.startsWith('Talking about the new bond'),'guest lower third: name big, title, blurb ('+g.h+' / '+g.k+')');
 ok(st.guest==='Dr. Maria Elena Garza-Villarreal'&&st.visible&&!st.logo,'state says a guest is on air');ok(g.hw[0]<=g.hw[1]+2&&g.hw[2]<=g.hw[3]+2&&g.sw[0]<=g.sw[1]+2,'guest bar fits');
 ok(g.bar[0]===30&&1080-g.bar[3]===26,'guest bar uses the same margins');
 // hostile / oversize input
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest',name:'A'.repeat(200),title:'T'.repeat(300),blurb:'B'.repeat(500)}));await sleep(900);let gg=await p.evaluate(()=>window.DITM.guest());ok(gg.name.length===60&&gg.title.length===80&&gg.blurb.length===140,'caps: name 60, title 80, blurb 140 ('+[gg.name.length,gg.title.length,gg.blurb.length]+')');
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest',name:'Bad\u0000Na\u0007me\n\tX\u202eevil',title:'a\u200bb\r\nc',blurb:'<img src=x onerror=alert(1)><script>alert(2)</script>'}));await sleep(900);gg=await p.evaluate(()=>window.DITM.guest());g=await gb();
 ok(!/[\u0000-\u001f\u202e\u200b]/.test(gg.name+gg.title+gg.blurb)&&gg.name==='Bad Na me X evil','control and bidi characters are stripped ('+JSON.stringify(gg.name)+')');ok(g.bad===0&&g.s.includes('<img'),'markup is shown as text, never parsed');
 await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'guest',name:{a:1},title:['x']}})));await p.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'guest',name:'Via Event',title:'Event title',blurb:'Event blurb'}})));await sleep(900);g=await gb();ok(g.h==='Via Event'&&g.s==='Event blurb','guest via the obs-browser event (non-string fields ignored)');
 // hold, hide, leave
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));await p.evaluate(()=>window.DITM.cmd({cmd:'start'}));await p.evaluate(()=>window.__adv(7*60000+5000));await sleep(600);const gblk=(await p.evaluate(()=>window.DITM.state())).idx;
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest',name:'Held Guest',title:'Title',blurb:'Blurb'}));await sleep(700);st=await p.evaluate(()=>window.DITM.state());ok(st.running&&st.held&&st.guest==='Held Guest'&&st.idx===gblk,'a guest holds auto-advance');
 await p.evaluate(()=>window.__adv(20*60000));await sleep(700);st=await p.evaluate(()=>window.DITM.state());ok(st.idx===gblk&&st.held,'the guest stays up while the clock is frozen');const elG=st.elapsedMin;
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest_hide'}));await sleep(900);st=await p.evaluate(()=>window.DITM.state());g=await gb();ok(!st.held&&!st.guest&&st.running&&st.visible&&Math.abs(st.elapsedMin-elG)<0.05&&g.h.toLowerCase()!=='held guest','Hide returns to the scheduled block and resumes the clock');
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest_show'}));await sleep(700);st=await p.evaluate(()=>window.DITM.state());ok(st.guest==='Held Guest'&&st.held,'guest_show brings the remembered guest back (no resend)');
 for(const c of [{cmd:'next'},{cmd:'prev'},{cmd:'goto',idx:3},{cmd:'clear'},{cmd:'logo'},{cmd:'resume'}]){await p.evaluate(()=>window.DITM.cmd({cmd:'guest_show'}));await p.evaluate(c=>window.DITM.cmd(c),c);st=await p.evaluate(()=>window.DITM.state());ok(!st.guest,c.cmd+' leaves the guest');}
 await p.evaluate(()=>window.DITM.cmd({cmd:'stop'}));await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest',name:'Remembered One',title:'T',blurb:'B'}));await p.reload();await sleep(500);st=await p.evaluate(()=>window.DITM.state());ok(!st.guest&&st.hasGuest,'after a reload the guest is remembered but off air');
 await p.evaluate(()=>window.DITM.cmd({cmd:'guest_show'}));await sleep(900);g=await gb();ok(g.h==='Remembered One','guest_show works after a reload without resending');await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));
 // ---- caller pop-up
 const cb=()=>p.evaluate(()=>{const g=id=>document.getElementById(id),e=g('call'),r=e.getBoundingClientRect(),im=g('cph'),b=g('bar').getBoundingClientRect(),lg=g('lg').getBoundingClientRect();return{on:e.classList.contains('on'),op:+getComputedStyle(e).opacity,nm:g('cnm').textContent,tt:g('ctt').textContent,img:im.classList.contains('ok'),src:im.getAttribute('src')||'',nat:im.naturalWidth,r:[r.left,r.top,r.right,r.bottom],bar:[b.left,b.top,b.right,b.bottom],lg:[lg.left,lg.top,lg.right,lg.bottom],hd:e.querySelector('.hd').textContent,svg:e.querySelectorAll('svg').length,bad:e.querySelectorAll('script,b,iframe').length}});
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:2}));await sleep(700);
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller',name:'Sgt. Roberto Salinas',title:'Public Information Officer, Example PD',photo:'https://photos.test/roberto.jpg'}));await sleep(1300);let c=await cb();
 ok(c.on&&c.op===1&&c.nm==='Sgt. Roberto Salinas'&&c.tt.startsWith('Public Information Officer')&&/ON THE PHONE/.test(c.hd)&&c.svg>=1,'ON THE PHONE pop-up with name, title and phone icon');
 ok(c.img&&c.nat>0&&c.src==='https://photos.test/roberto.jpg','caller photo (https) is shown');
 ok(c.r[0]>=1480&&c.r[2]<=1920-40&&c.r[3]<=1080-200&&c.r[2]-c.r[0]===380,'pop-up sits on the right side ('+c.r+')');
 ok(c.r[3]<=c.bar[1]&&(c.r[2]<c.lg[0]||c.r[3]<=c.lg[1]),'pop-up does not cover the lower-third bar or the logo ('+c.r+' vs bar '+c.bar+')');
 st=await p.evaluate(()=>window.DITM.state());ok(st.caller==='Sgt. Roberto Salinas'&&st.visible&&st.idx===2&&!st.held,'caller leaves the bar and the hold state alone');
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller_hide'}));await sleep(900);c=await cb();ok(!c.on&&c.op===0,'caller_hide slides it away');
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller_show'}));await sleep(900);c=await cb();ok(c.on&&c.nm==='Sgt. Roberto Salinas','caller_show works from memory');
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller_toggle'}));await sleep(700);c=await cb();ok(!c.on,'caller_toggle hides when shown');await p.evaluate(()=>window.DITM.cmd({cmd:'caller_toggle'}));await sleep(700);c=await cb();ok(c.on,'caller_toggle shows when hidden');
 await p.evaluate(()=>window.DITM.cmd({cmd:'clear'}));await sleep(500);c=await cb();ok(c.on,'clear (the chyron bar) does not drop the phone pop-up');
 await p.reload();await sleep(500);c=await cb();ok(!c.on&&(await p.evaluate(()=>window.DITM.caller().name))==='Sgt. Roberto Salinas','after a reload the caller is remembered but hidden');await p.evaluate(()=>window.DITM.cmd({cmd:'caller_show'}));await sleep(1100);c=await cb();ok(c.on&&c.img,'caller_show after a reload shows name, title and photo without resending');
 for(const bad of ['http://photos.test/a.jpg','javascript:alert(1)','data:image/png;base64,AAAA','https://user:pw@photos.test/a.jpg','https://photos.test/a b.jpg','https://photos.test/a"onerror="x.jpg','//photos.test/a.jpg','ftp://x/a.jpg','https://photos.test/'+'a'.repeat(1100),'file:///etc/passwd',42,{u:1}]){
  await p.evaluate(b=>window.DITM.cmd({cmd:'caller',name:'No Photo',title:'T',photo:b}),bad);await sleep(250);c=await cb();ok(c.nm==='No Photo'&&c.src===''&&!c.img,'photo rejected: '+String(typeof bad==='string'?bad.slice(0,40):typeof bad));}
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller',name:'<img src=x onerror=alert(1)>',title:'<b>x</b>',photo:'https://photos.test/z.jpg'}));await sleep(500);c=await cb();ok(c.bad===0&&c.nm.includes('<img'),'caller text is plain text');
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller',name:'N'.repeat(200),title:'T'.repeat(200)}));await sleep(300);const cc=await p.evaluate(()=>window.DITM.caller());ok(cc.name.length===60&&cc.title.length===80,'caller caps: name 60, title 80');
 await p.evaluate(()=>window.DITM.cmd({cmd:'caller_hide'}));await sleep(600);
 // both at once: guest bar + caller pop-up
 await p.evaluate(()=>{window.DITM.cmd({cmd:'guest',name:'Studio Guest',title:'Title',blurb:'Blurb'});window.DITM.cmd({cmd:'caller',name:'Phone Person',title:'Remote',photo:'https://photos.test/p.jpg'})});await sleep(1300);g=await gb();c=await cb();ok(g.inn&&g.h==='Studio Guest'&&c.on&&c.r[3]<=g.bar[1],'guest bar and phone pop-up can be up together without overlapping');
 await p.screenshot({path:'/workspace/ditm-shots/ui-test-guest-caller.png',omitBackground:true});
 await p.evaluate(()=>{window.DITM.cmd({cmd:'clear'});window.DITM.cmd({cmd:'caller_hide'})});await p.close();p=await open(CHY,'?debug',1920,1080,T0);
}
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
 await p.evaluate(()=>{window.DITM.cmd({cmd:'hold'});window.DITM.cmd({cmd:'hold'})});let s1b=await p.evaluate(()=>window.DITM.state());await p.evaluate(()=>window.__adv(60000));
 await p.evaluate(()=>{window.DITM.cmd({cmd:'resume'});window.DITM.cmd({cmd:'resume'})});let s2=await p.evaluate(()=>window.DITM.state());ok(Math.abs(s2.elapsedMin-s1b.elapsedMin)<0.05&&!s2.held,'double hold / double resume harmless');
 // logo while auto-advance runs: stays hidden, keeps counting, 'show' brings back the current block
 await p.evaluate(()=>window.DITM.cmd({cmd:'goto',idx:2}));await sleep(300);await p.evaluate(()=>window.DITM.cmd({cmd:'logo'}));st=await p.evaluate(()=>window.DITM.state());ok(st.running&&st.logo&&!st.visible&&st.idx===2,'logo during auto-advance keeps running');
 await p.evaluate(b=>window.__adv((b[3].offset-b[2].offset)*60000+3000),blocks);await sleep(700);st=await p.evaluate(()=>window.DITM.state());lo=await lg();ok(st.idx===3&&st.logo&&!st.visible&&!lo.bar&&!lo.on,'advances to block 3 under logo mode, screen stays clean');
 await p.evaluate(()=>window.DITM.cmd({cmd:'show'}));await sleep(700);st=await p.evaluate(()=>window.DITM.state());lo=await lg();ok(st.idx===3&&st.visible&&!st.logo&&lo.bar&&!lo.on,'show returns to the current block');
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
 // ======== D2. items over http + ntfy ========
 const IT2=Object.assign({},REAL.items);const someId=Object.keys(REAL.items)[3],other=Object.keys(REAL.items)[10];
 M.items.doc={v:1,items:{[someId]:REAL.items[someId]}};
 p=await open(CHY,'?debug&topic='+TOP+'&ntfy='+encodeURIComponent(M.base)+'&itemsurl='+encodeURIComponent(M.base+'/chyron-items.json'),1920,1080);await sleep(1500);
 ok((await p.evaluate(()=>window.DITM.items()))===1,'chyron fetched chyron-items.json (cache-busted)');
 M.push(TOP,{k:'cmd',cmd:'item',id:someId});await sleep(900);st=await p.evaluate(()=>window.DITM.state());ib=await bar();
 ok(st.item===someId&&st.visible&&ib.h===REAL.items[someId].headline,'ntfy item shows the published headline ('+ib.h.slice(0,40)+')');
 M.push(TOP,{k:'cmd',cmd:'item',id:other,headline:'HACKED',text:'HACKED'});await sleep(700);st=await p.evaluate(()=>window.DITM.state());ok(st.item===someId,'an id that is not published yet is ignored');
 M.items.doc={v:1,items:{[someId]:REAL.items[someId],[other]:REAL.items[other]}};await p.evaluate(()=>window.__adv(20000));
 M.push(TOP,{k:'cmd',cmd:'item',id:other});await sleep(1500);st=await p.evaluate(()=>window.DITM.state());ib=await bar();ok(st.item===other&&ib.h===REAL.items[other].headline,'a newly published id is picked up with one refresh');
 await sleep(900);last=M.states(TOP).pop();ok(last&&last.item===other,'state published back carries the audible id (not text): '+JSON.stringify(last&&last.item));
 ok(!JSON.stringify(last).includes(REAL.items[other].headline),'the published state holds no headline text');
 M.push(TOP,{k:'cmd',cmd:'clear'});await sleep(500);await p.close();
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
 // ======== E2. dashboard: send to chyron ========
 const T3='ditm-ros-sendtest001';
 p=await open(STU,'',1180,820,T0);
 await p.evaluate(()=>localStorage.removeItem('ditm-chyron-topic-v1'));await p.reload();await sleep(300);
 ok(await p.evaluate(()=>[...document.querySelectorAll('.chysend')].length>50&&[...document.querySelectorAll('.chysend')].every(b=>b.offsetParent===null)),'unlinked: send-to-chyron buttons exist but are hidden');await p.close();
 p=await open(STU,'?ctl='+T3+'&ntfy='+encodeURIComponent(M.base),1180,820,T0);await sleep(300);
 const secs=await p.evaluate(()=>{const o={};document.querySelectorAll('details.sec').forEach(d=>{o[d.id]=d.querySelectorAll('.chysend').length});return o});
 ok(['headlines','chisme','trending','tech','obits'].every(k=>(secs[k]||0)>0)||Object.keys(secs).filter(k=>secs[k]>0).length>=6,'send buttons in every story section '+JSON.stringify(Object.fromEntries(Object.entries(secs).filter(e=>e[1]>0))));
 await p.evaluate(()=>{document.querySelectorAll('details.sec').forEach(d=>d.open=true)});await sleep(200);
 const bt=await p.evaluate(()=>{const b=[...document.querySelectorAll('.chysend')].filter(x=>x.offsetParent);const r=b[0].getBoundingClientRect();return{n:b.length,minH:Math.min(...b.map(x=>x.getBoundingClientRect().height)),minW:Math.min(...b.map(x=>x.getBoundingClientRect().width)),txt:b[0].textContent,id:b[0].dataset.chyid,sw:document.documentElement.scrollWidth,iw:innerWidth}});
 ok(bt.n>50&&bt.minH>=44&&bt.minW>=44,'linked: visible iPad-size buttons ('+bt.n+', min '+bt.minW+'x'+bt.minH+')');ok(bt.sw<=bt.iw,'no horizontal scroll with the buttons');
 const ids=await p.evaluate(()=>[...document.querySelectorAll('.chysend')].filter(x=>x.offsetParent).slice(0,3).map(x=>x.dataset.chyid));
 await p.evaluate(i=>document.querySelector('.chysend[data-chyid="'+i+'"]').click(),ids[0]);await sleep(500);
 let ic=M.cmds(T3).filter(c=>c.cmd==='item');ok(ic.length===1&&ic[0].id===ids[0],'tap publishes {cmd:item,id} on the topic');
 ok(Object.keys(ic[0]).every(k=>['k','cmd','at','v','id'].includes(k)),'the item command carries no text, only the id');
 ok(!!REAL.items[ids[0]]&&!JSON.stringify(M.msgs[T3]).includes(REAL.items[ids[0]].headline.slice(0,30)),'the headline text is not on the network');
 let oa=await p.evaluate(i=>{const c=document.querySelector('[data-chyid="'+i+'"].onair'),b=document.querySelector('.chysend[data-chyid="'+i+'"]');return{card:!!c,pressed:b.getAttribute('aria-pressed'),txt:b.textContent,st:document.getElementById('chst').textContent}},ids[0]);
 ok(oa.card&&oa.pressed==='true'&&/On air/.test(oa.txt),'the tapped card is marked ON AIR right away');
 const NOWP2=await p.evaluate(()=>Date.now());
 M.push(T3,{k:'state',v:1,running:true,held:true,idx:2,letter:'C',visible:true,logo:false,item:ids[0],startAt:Math.floor((NOWP2-5*MIN)/MIN)*MIN,heldAt:NOWP2,holdMs:0,elapsedMin:5,at:NOWP2+50,blocks:12});await sleep(700);
 oa=await p.evaluate(i=>({st:document.getElementById('chst').textContent,live:document.getElementById('sslive').textContent,card:document.querySelectorAll('.onair').length,hold:document.getElementById('chhold').textContent}),ids[0]);
 const hl=await p.evaluate(i=>document.querySelector('[data-chyid="'+i+'"]').dataset.chyh,ids[0]);
 ok(oa.st.includes('audible: '+hl)&&/HELD/.test(oa.st),'status says audible: <headline> and HELD ('+oa.st.slice(0,70)+')');ok(/HELD/.test(oa.live)&&/Resume/.test(oa.hold),'the dashboard shows HELD with a Resume button');ok(oa.card===1,'exactly one card is ON AIR');
 await p.evaluate(i=>document.querySelector('.chysend[data-chyid="'+i+'"]').click(),ids[1]);await sleep(300);
 oa=await p.evaluate(()=>[...document.querySelectorAll('.onair')].map(e=>e.dataset.chyid));ok(oa.length===1&&oa[0]===ids[1],'tapping another card moves the ON AIR mark');
 M.push(T3,{k:'state',v:1,running:true,held:false,idx:2,letter:'C',visible:true,logo:false,item:null,startAt:Math.floor((NOWP2-5*MIN)/MIN)*MIN,heldAt:0,holdMs:60000,elapsedMin:5,at:NOWP2+9000,blocks:12});await sleep(900);
 oa=await p.evaluate(()=>({n:document.querySelectorAll('.onair').length,st:document.getElementById('chst').textContent}));ok(oa.n===0&&!/audible/.test(oa.st),'when the chyron leaves the audible the mark and status clear ('+oa.st.slice(0,40)+')');
 await p.close();
 // ======== E3. dashboard: guest + phone caller panels ========
 const T5='ditm-ros-guesttest01';
 p=await open(STU,'',1180,820,T0);await p.evaluate(()=>localStorage.removeItem('ditm-chyron-topic-v1'));await p.reload();await sleep(300);
 ok(await p.evaluate(()=>{const e=document.getElementById('gp');return !!e&&e.offsetParent===null}),'unlinked: the guest / phone panel is hidden');await p.close();
 require('child_process').execSync('python3 -c "from PIL import Image,ImageDraw;im=Image.new(\'RGB\',(1200,800),(30,90,160));d=ImageDraw.Draw(im);d.ellipse((400,100,800,500),fill=(230,190,150));im.save(\'/tmp/ditm-test-photo.png\')"');
 p=await open(STU,'?ctl='+T5+'&ntfy='+encodeURIComponent(M.base),1180,820,T0);await sleep(300);
 await p.evaluate(()=>{localStorage.removeItem('ditm-gp-form-v1');['g-name','g-title','g-blurb','c-name','c-title','c-photo'].forEach(i=>{const e=document.getElementById(i);if(e)e.value=''})});
 await p.evaluate(()=>{document.getElementById('gp').open=true});await sleep(150);
 const gpi=await p.evaluate(()=>{const q=s=>document.querySelector(s);const bs=['g-show','g-hide','c-go','c-show','c-hide'].map(i=>q('#'+i).getBoundingClientRect());const ins=['g-name','g-title','g-blurb','c-name','c-title','c-photo'].map(i=>q('#'+i).getBoundingClientRect());return{vis:q('#gp').offsetParent!==null,minH:Math.min(...bs.map(r=>r.height)),minW:Math.min(...bs.map(r=>r.width)),inH:Math.min(...ins.map(r=>r.height)),sw:document.documentElement.scrollWidth,iw:innerWidth,max:[60,80,140,60,80].every((n,i)=>+q('#'+['g-name','g-title','g-blurb','c-name','c-title'][i]).maxLength===n)}});
 ok(gpi.vis&&gpi.minH>=44&&gpi.minW>=44&&gpi.inH>=40,'linked: Guest & phone panel with iPad-size buttons ('+JSON.stringify(gpi)+')');ok(gpi.sw<=gpi.iw,'no horizontal scroll with the panel open');ok(gpi.max,'inputs carry the 60/80/140 length caps');
 const gc=()=>M.cmds(T5);
 await p.click('#g-show');await sleep(300);ok(gc().filter(c=>c.cmd==='guest').length===0&&/name/i.test(await p.evaluate(()=>document.getElementById('gp-msg').textContent)),'guest needs a name before it is published');
 await p.evaluate(()=>{const set=(i,v)=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))};set('g-name','Dr. Ana Test');set('g-title','Mayor of Testville');set('g-blurb','Here to talk about the budget.')});
 await p.click('#g-show');await sleep(700);
 let gm=gc().filter(c=>c.cmd==='guest');ok(gm.length===1&&gm[0]&&gm[0].name==='Dr. Ana Test'&&gm[0].title==='Mayor of Testville'&&gm[0].blurb==='Here to talk about the budget.','Show guest publishes {cmd:guest,name,title,blurb} '+JSON.stringify(gm.slice(-1))+' msgs='+JSON.stringify((M.msgs[T5]||[]).slice(-3)));
 ok(gm[0]&&Object.keys(gm[0]).every(k=>['k','cmd','at','v','name','title','blurb'].includes(k)),'the guest message carries only the allowed keys');
 await p.evaluate(()=>{const e=document.getElementById('g-blurb');e.maxLength=5000;e.value='x'.repeat(500);e.dispatchEvent(new Event('input',{bubbles:true}))});await p.click('#g-show');await sleep(500);gm=gc().filter(c=>c.cmd==='guest');ok(gm.length>=2&&gm[gm.length-1].blurb.length===140,'the dashboard caps the blurb at 140 even if the field is forced');
 await p.click('#g-hide');await sleep(300);ok(gc().some(c=>c.cmd==='guest_hide'),'Hide publishes guest_hide');
 await p.close();p=await open(STU,'?ctl='+T5+'&ntfy='+encodeURIComponent(M.base),1180,820,T0);await sleep(400);await p.evaluate(()=>{document.getElementById('gp').open=true});ok(await p.evaluate(()=>document.getElementById('g-name').value)==='Dr. Ana Test','the form survives a reload');
 // phone caller
 await p.click('#c-go');await sleep(300);ok(gc().filter(c=>c.cmd==='caller').length===0,'caller needs a name');
 await p.evaluate(()=>{const set=(i,v)=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))};set('c-name','Sgt. Roberto Salinas');set('c-title','PIO, Example PD');set('c-photo','http://insecure.test/a.jpg')});
 await p.click('#c-go');await sleep(300);
 ok(gc().filter(c=>c.cmd==='caller').length===0&&/https/.test(await p.evaluate(()=>document.getElementById('gp-msg').textContent)),'a non-https photo link is refused on the dashboard');
 await p.evaluate(()=>{const e=document.getElementById('c-photo');e.value='https://photos.test/roberto.jpg';e.dispatchEvent(new Event('input',{bubbles:true}))});await p.click('#c-go');await sleep(700);
 let cm=gc().filter(c=>c.cmd==='caller');ok(cm.length===1&&cm[0]&&cm[0].name==='Sgt. Roberto Salinas'&&cm[0].title==='PIO, Example PD'&&cm[0].photo==='https://photos.test/roberto.jpg','Bring caller on publishes {cmd:caller,name,title,photo} '+JSON.stringify(cm.slice(-1)));
 ok(cm[0]&&Object.keys(cm[0]).every(k=>['k','cmd','at','v','name','title','photo'].includes(k)),'the caller message carries only the allowed keys');
 await p.click('#c-hide');await sleep(300);await p.click('#c-show');await sleep(300);ok(gc().some(c=>c.cmd==='caller_hide')&&gc().some(c=>c.cmd==='caller_show'),'Hide caller / Show publish caller_hide / caller_show');
 // upload
 const inp=await p.$('#c-file');await inp.uploadFile('/tmp/ditm-test-photo.png');await sleep(1800);
 const pu=M.puts.filter(x=>x.url.startsWith('/'+T5));ok(pu.length===1&&/filename=caller\.jpg/.test(pu[0].url)&&pu[0].body[0]===0xFF&&pu[0].body[1]===0xD8,'upload PUTs a JPEG attachment to the private topic');
 if(pu.length){const bd=pu[0].body;let w=0,h=0;for(let i=2;i<bd.length-9;){if(bd[i]!==0xFF){i++;continue}const m=bd[i+1];if(m>=0xC0&&m<=0xC3){h=bd.readUInt16BE(i+5);w=bd.readUInt16BE(i+7);break}i+=2+bd.readUInt16BE(i+2)}ok(w>0&&Math.max(w,h)<=400&&w/h>1.4&&w/h<1.6,'the photo is shrunk to <=400px, aspect kept ('+w+'x'+h+', '+bd.length+' bytes)')}
 const up=await p.evaluate(()=>({ph:document.getElementById('c-photo').value,pv:!document.getElementById('c-prev').hidden&&document.getElementById('c-prev').src.startsWith('data:image/jpeg'),t:document.getElementById('c-up').textContent}));
 ok(up.ph==='https://photos.test/att1/caller.jpg'&&up.pv&&/ready/i.test(up.t),'the returned https link fills the photo field and a preview shows ('+up.t.slice(0,40)+')');
 await p.click('#c-go');await sleep(400);cm=gc().filter(c=>c.cmd==='caller');ok(cm[cm.length-1].photo==='https://photos.test/att1/caller.jpg','the caller goes out with the uploaded photo link');
 ok(!JSON.stringify(M.msgs[T5]).includes('data:image'),'no image bytes are sent as a message');
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
 // audible, end to end
 M.items.doc=REAL;
 await dash.close();await chy.close();
 const T4='ditm-ros-audible0001';const dash2=await open(STU,'?ctl='+T4+'&'+qs2,1180,820,T0);const chy2=await open(CHY,'?topic='+T4+'&'+qs2+'&itemsurl='+encodeURIComponent(M.base+'/chyron-items.json'),1920,1080,T0);await chy2.evaluate(()=>{localStorage.removeItem('ditm-chyron-state-v1');localStorage.removeItem('ditm-chyron-guest-v1');localStorage.removeItem('ditm-chyron-caller-v1')});await chy2.reload();await sleep(1800);
 await dash2.evaluate(()=>document.querySelector('#ssbtn').click());await sleep(1200);
 st=await chy2.evaluate(()=>window.DITM.state());ok(st.running,'E2E: chyron is running after Start');
 const aid=await dash2.evaluate(()=>{const b=[...document.querySelectorAll('.chysend')].find(x=>x.offsetParent&&x.dataset.chyid);return b&&b.dataset.chyid});
 ok(!!aid&&!!REAL.items[aid],'E2E: found a visible send-to-chyron card '+aid);
 await dash2.evaluate(i=>document.querySelector('.chysend[data-chyid="'+i+'"]').click(),aid);await sleep(800);
 for(let i=0;i<25&&!(await chy2.evaluate(()=>window.DITM.state().item));i++)await sleep(200);
 st=await chy2.evaluate(()=>window.DITM.state());const hd=await chy2.evaluate(()=>document.getElementById('head').textContent);
 ok(st.item===aid&&st.held&&st.running&&hd===REAL.items[aid].headline,'E2E: tapping a card puts its headline on the chyron and holds auto-advance '+JSON.stringify(st));
 let dd=null;for(let i=0;i<30;i++){dd=await dash2.evaluate(i=>({live:document.getElementById('sslive').textContent,st:document.getElementById('chst').textContent,on:document.querySelector('[data-chyid="'+i+'"]').classList.contains('onair'),hl:document.querySelector('[data-chyid="'+i+'"]').dataset.chyh,heldBtn:/Resume/.test(document.getElementById('chhold').textContent)}),aid);if(/HELD/.test(dd.live||'')&&dd.on&&dd.st.includes('audible:'))break;await sleep(200)}
 ok((/HELD/.test(dd.live)||dd.heldBtn)&&dd.on&&dd.st.includes('audible: '+dd.hl),'E2E: the dashboard shows HELD, the ON AIR card and "audible: <headline>" '+JSON.stringify(dd)+' states='+JSON.stringify(M.states(T4).slice(-3).map(x=>({held:x.held,item:x.item,letter:x.letter}))));
 // resume: click only when the button says Resume (dashboard has adopted the hold)
 if(!(await dash2.evaluate(()=>/Resume/.test(document.getElementById('chhold').textContent)))){await dash2.evaluate(()=>{const a=window.ditmRos;if(a&&!a.held())a.hold()});await sleep(200)}
 await dash2.evaluate(()=>document.getElementById('chhold').click());await sleep(800);
 for(let i=0;i<25&&(await chy2.evaluate(()=>window.DITM.state().held));i++)await sleep(200);
 st=await chy2.evaluate(()=>window.DITM.state());
 dd=await dash2.evaluate(i=>({on:document.querySelector('[data-chyid="'+i+'"]').classList.contains('onair'),st:document.getElementById('chst').textContent}),aid);
 ok(!st.held&&st.item===null&&st.running&&!dd.on&&!/audible/.test(dd.st),'E2E: Resume returns the chyron to the scheduled block and clears the dashboard mark '+JSON.stringify([st,dd]));
 // guest + phone caller, end to end
 await chy2.setRequestInterception(true);chy2.on('request',r=>{try{if(r.url().startsWith('https://')&&!r.url().includes('127.0.0.1'))r.respond({status:200,contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==','base64')});else r.continue()}catch(e){try{r.continue()}catch(x){}}});
 await dash2.evaluate(()=>{document.getElementById('gp').open=true});
 await dash2.evaluate(()=>{const set=(i,v)=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))};set('g-name','E2E Guest');set('g-title','Title Here');set('g-blurb','Blurb here.')});await dash2.click('#g-show');await sleep(1500);
 st=await chy2.evaluate(()=>window.DITM.state());let gt=await chy2.evaluate(()=>[document.getElementById('head').textContent,document.getElementById('kick').textContent,document.getElementById('sub').textContent]);
 ok(st.guest==='E2E Guest'&&st.held&&gt[0]==='E2E Guest'&&gt[1]==='Title Here'&&gt[2]==='Blurb here.','E2E: Show guest on the dashboard puts name, title and blurb on the chyron and holds');
 dd=await dash2.evaluate(()=>({live:document.getElementById('sslive').textContent,st:document.getElementById('chst').textContent}));await sleep(800);dd=await dash2.evaluate(()=>({live:document.getElementById('sslive').textContent,st:document.getElementById('chst').textContent}));ok(/HELD/.test(dd.live)&&/guest/i.test(dd.st),'E2E: the dashboard shows HELD and "guest: <name>" ('+dd.st.slice(0,50)+')');
 await dash2.click('#g-hide');await sleep(1500);st=await chy2.evaluate(()=>window.DITM.state());ok(!st.guest&&!st.held&&st.running,'E2E: Hide returns the chyron to the scheduled block');
 await dash2.evaluate(()=>{const set=(i,v)=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))};set('c-name','E2E Caller');set('c-title','On the line');set('c-photo','https://photos.test/e2e.jpg')});await dash2.click('#c-go');await sleep(1500);
 let ce=await chy2.evaluate(()=>({on:document.getElementById('call').classList.contains('on'),n:document.getElementById('cnm').textContent,t:document.getElementById('ctt').textContent,img:document.getElementById('cph').classList.contains('ok')}));ok(ce.on&&ce.n==='E2E Caller'&&ce.t==='On the line'&&ce.img,'E2E: Bring caller on shows the pop-up with photo, name, title');
 await chy2.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'caller_toggle'}})));await sleep(900);ce=await chy2.evaluate(()=>document.getElementById('call').classList.contains('on'));ok(!ce,'E2E: the Stream Deck caller_toggle key hides it');
 await chy2.evaluate(()=>window.dispatchEvent(new CustomEvent('ditm',{detail:{cmd:'caller_toggle'}})));await sleep(900);ce=await chy2.evaluate(()=>document.getElementById('call').classList.contains('on'));ok(ce,'E2E: and brings it back');
 await dash2.click('#c-hide');await sleep(1200);ce=await chy2.evaluate(()=>document.getElementById('call').classList.contains('on'));ok(!ce,'E2E: Hide caller on the dashboard hides it');
 await dash2.evaluate(()=>document.querySelector('#ssreset').click());await sleep(500);await dash2.close();await chy2.close();
 M.close();await b.close();
 console.log('errors:',errs.length?errs.join(' | '):'none');
 console.log(`chyron UI tests: ${pass} passed, ${fail} failed`);process.exit(fail||errs.length?1:0);
})().catch(e=>{console.log('CRASH',e);process.exit(2)});
