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
 console.log('ERRORS',JSON.stringify(errs));
 await b.close();
})();
