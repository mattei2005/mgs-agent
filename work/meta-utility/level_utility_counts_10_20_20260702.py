#!/usr/bin/env python3
import asyncio,json,pathlib,re,datetime as dt,csv
from copy import deepcopy
from zoneinfo import ZoneInfo
import importlib.util
BASE=pathlib.Path('/root/mgs-agent'); TRACK=BASE/'data/sb-utility-rollout-tracker.json'; BACK=BASE/'backups/sb-templates'; OUT=BASE/'work/meta-utility/level-counts-20260702'; TZ=ZoneInfo('America/New_York')
spec=importlib.util.spec_from_file_location('mgr', BASE/'scripts/sb-utility-rollout-manager.py'); mgr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mgr)
OUT.mkdir(parents=True,exist_ok=True); BACK.mkdir(parents=True,exist_ok=True)
def safe(s): return re.sub(r'[^a-zA-Z0-9._-]+','-',s.lower()).strip('-')[:95]
def link(m): return m.get('LINK_1') or m.get('LINK 1') or ''
def key(m): return (re.sub(r'\s+',' ',(m.get('TEXT') or '')).strip().lower(), (m.get('CTA_1') or m.get('CTA 1') or '').strip().lower())
def clean(m,i,slot_link):
    x=deepcopy(m); x['MESSAGE_ID']=i; x['LINK_1']=slot_link
    for k in ['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']: x.pop(k,None)
    return x
def status_of(m):
    if int(m.get('INVALID_FORMAT') or 0)>0: return 'INVALID'
    if int(m.get('REJECTED') or 0)>0: return 'REJECTED'
    if int(m.get('ERROR') or 0)>0: return 'ERROR'
    if int(m.get('APPROVED') or 0)>0: return 'APPROVED'
    return 'GRAY'
def build(row,t,target):
    cur=sorted(mgr.parse_messages(row),key=lambda x:int(x.get('MESSAGE_ID') or 0))
    srcrow=json.load(open(t['source_bank_json'])); src=sorted(mgr.parse_messages(srcrow),key=lambda x:int(x.get('MESSAGE_ID') or 0))
    chosen=[]; used=set()
    # keep current first, without duplicates
    for m in cur:
        k=key(m)
        if k in used: continue
        chosen.append(m); used.add(k)
        if len(chosen)>=target: break
    # add from source bank if needed
    for m in src:
        if len(chosen)>=target: break
        k=key(m)
        if k in used: continue
        chosen.append(m); used.add(k)
    if len(chosen)<target: raise RuntimeError(f"not enough unique messages for {row.get('NAME')}: {len(chosen)}/{target}")
    out=[]
    for i,m in enumerate(chosen[:target],1):
        if i-1>=len(src): raise RuntimeError(f"no source link slot {i} for {row.get('NAME')}")
        out.append(clean(m,i,link(src[i-1])))
    return out
async def main():
    tag=dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
    p,b,ctx,page,rows,headers,post_url=await mgr.capture_rows_headers()
    try:
        tracker=json.load(open(TRACK)); by={r.get('NAME'):r for r in rows}; results=[]
        for t in tracker['templates']:
            name=t['name']; row=by.get(name)
            if not row: results.append({'template':name,'ok':False,'error':'not found live'}); continue
            pages=int(row.get('PAGES') or 0); cur=mgr.parse_messages(row); before=len(cur); target=20 if pages>0 else 10
            if before==target:
                # validate links already
                results.append({'template':name,'ok':True,'changed':False,'pages':pages,'before':before,'after':target})
                t['pages']=pages; t['active_target']=target
                continue
            new=build(row,t,target)
            bpath=BACK/f'{safe(name)}-before-level-{target}-{tag}.json'; mgr.save_json(bpath,row)
            payload=deepcopy(row); payload['MESSAGES']=json.dumps(new,ensure_ascii=False,separators=(',',':'))
            resp=await ctx.request.post(post_url,headers=headers,data=json.dumps(payload,ensure_ascii=False)); body=(await resp.text())[:200]
            ok=200<=resp.status<300
            results.append({'template':name,'ok':ok,'changed':ok,'pages':pages,'before':before,'after':target,'post_status':resp.status,'error':None if ok else body,'backup':str(bpath)})
            if ok:
                t['pages']=pages; t['active_target']=target; t['last_action_date']=dt.datetime.now(TZ).date().isoformat(); t['last_action']=f'manual_level_to_{target}_by_pages'; t.setdefault('history',[]).append({'date':dt.datetime.now(TZ).date().isoformat(),'action':t['last_action'],'before':before,'after':target,'pages':pages,'backup_json':str(bpath)})
        tb=TRACK.with_suffix(f'.before-level-10-20-{tag}.json'); tb.write_text(json.dumps(tracker,ensure_ascii=False,indent=2)); TRACK.write_text(json.dumps(tracker,ensure_ascii=False,indent=2))
        # recapture live report
        p2,b2,ctx2,page2,rows2,headers2,post_url2=await mgr.capture_rows_headers()
        try:
            by2={r.get('NAME'):r for r in rows2}; report=[]
            for t in tracker['templates']:
                r=by2[t['name']]; msgs=mgr.parse_messages(r); c={s:0 for s in ['APPROVED','GRAY','REJECTED','ERROR','INVALID']}
                for m in msgs: c[status_of(m)]+=1
                bad=c['REJECTED']+c['ERROR']+c['INVALID']; parts=[]
                if bad: parts.append('bad='+str(bad)+' '+ '/'.join(f'{k}={c[k]}' for k in ['REJECTED','ERROR','INVALID'] if c[k]))
                if c['GRAY']: parts.append(f"gray={c['GRAY']}")
                if c['APPROVED']: parts.append(f"approved={c['APPROVED']}")
                report.append({'template':t['name'],'pages':int(r.get('PAGES') or 0),'msgs':len(msgs),'motivo':' | '.join(parts) if parts else '-'})
        finally:
            await b2.close(); await p2.stop()
        out={'executed_at_et':dt.datetime.now(TZ).isoformat(timespec='seconds'),'results':results,'tracker_backup':str(tb),'report':report}
        jp=OUT/f'level-10-20-report-{tag}.json'; jp.write_text(json.dumps(out,ensure_ascii=False,indent=2))
        cp=OUT/f'level-10-20-report-{tag}.csv'
        with cp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['template','pages','msgs','motivo']); w.writeheader(); w.writerows(report)
        print(json.dumps({'status':'OK' if all(r.get('ok') for r in results) else 'WARN','changed':sum(1 for r in results if r.get('changed')),'reported':len(report),'json':str(jp),'csv':str(cp),'counts':{'10':sum(1 for r in report if r['msgs']==10),'20':sum(1 for r in report if r['msgs']==20),'other':sum(1 for r in report if r['msgs'] not in (10,20))}},ensure_ascii=False))
        print('---ROWS---')
        for r in report: print(f"{r['template']}\t{r['pages']}\t{r['msgs']}\t{r['motivo']}")
    finally:
        await b.close(); await p.stop()
asyncio.run(main())
