#!/usr/bin/env node
const base = 'http://127.0.0.1:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function openTarget() {
  const r = await fetch(base + '/json/new?about:blank', {method:'PUT'});
  if (!r.ok) throw new Error(`new target ${r.status}`);
  return r.json();
}
async function run() {
  const target = await openTarget();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve; ws.onerror=reject;});
  let seq=0; const pending=new Map(); const listeners=new Map();
  ws.onmessage = e => {
    const m=JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { const {resolve,reject}=pending.get(m.id); pending.delete(m.id); return m.error?reject(new Error(JSON.stringify(m.error))):resolve(m.result); }
    const list=listeners.get(m.method)||[]; listeners.set(m.method,[]); for(const fn of list) fn(m.params||{});
  };
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
  const once=(method,timeout=30000)=>new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error(`timeout ${method}`)),timeout); const a=listeners.get(method)||[]; a.push(p=>{clearTimeout(t);resolve(p)}); listeners.set(method,a);});
  const evalv=async expression => (await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  const results=[];
  for (const slug of ['sh2-g002','sh1-g002']) {
    const url=`https://yolokfx.com/quiz/us/${slug}/?utm_source=facebook&utm_medium=g002-s&utm_campaign=static_canary&utm_adgroup=g002-test&fbclid=STATIC123&custom_x=abc`;
    const loaded=once('Page.loadEventFired'); await send('Page.navigate',{url}); await loaded; await sleep(500);
    const state=await evalv(`(() => {const c=[...document.querySelectorAll('[data-mgs-dq-cta]')];const href=c[0]?.href||'';const u=href?new URL(href):null;const counts={};if(u)for(const k of ['utm_source','utm_medium','utm_campaign','utm_adgroup','fbclid','custom_x'])counts[k]=u.searchParams.getAll(k).length;const r=c[0]?.getBoundingClientRect();return {title:document.title,marker:document.documentElement.outerHTML.includes('MGS Direct Quiz static; plugin=1.1.0'),forms:document.forms.length,inputs:document.querySelectorAll('input').length,ctas:c.length,href,counts,scrollWidth:document.documentElement.scrollWidth,innerWidth,card:document.querySelector('.mgs-dq-card')?.getBoundingClientRect().toJSON(),ctaRect:r?.toJSON()};})()`);
    const r=state.ctaRect;
    if (!r) throw new Error(`CTA missing ${slug}`);
    const nav=once('Page.loadEventFired');
    const x=r.x+r.width/2,y=r.y+r.height/2;
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1});
    await nav; await sleep(400);
    const finalUrl=await evalv('location.href');
    results.push({slug,...state,final_url:finalUrl,destination_ok:finalUrl.startsWith('https://yolokfx.com/rec-us-app-shein-circle-of-style/')});
  }
  ws.close();
  await fetch(base + '/json/close/' + target.id);
  console.log(JSON.stringify(results));
}
run().catch(e=>{console.error(e.stack||e);process.exit(1)});
