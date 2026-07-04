#!/usr/bin/env python3
import asyncio, csv, json, pathlib, re, datetime as dt
from copy import deepcopy
from zoneinfo import ZoneInfo
import importlib.util

BASE=pathlib.Path('/root/mgs-agent')
TRACKER=BASE/'data/sb-utility-rollout-tracker.json'
BACKUP=BASE/'backups/sb-templates'
OUT=BASE/'work/meta-utility/link-slot-fix-20260702'
TZ=ZoneInfo('America/New_York')
spec=importlib.util.spec_from_file_location('mgr', BASE/'scripts/sb-utility-rollout-manager.py')
mgr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mgr)

def safe_name(s): return re.sub(r'[^a-zA-Z0-9._-]+','-',s.lower()).strip('-')[:90]
def link(m): return m.get('LINK_1') or m.get('LINK 1') or ''
def seq(u):
    m=re.search(r'(?:mct|bd|jbf|ym|av)-([0-9]{3}(?:-2)?)', u or '', re.I)
    return m.group(1) if m else ''

def audit_and_fix(row,t):
    current=sorted(mgr.parse_messages(row), key=lambda x:int(x.get('MESSAGE_ID') or 0))
    source_row=json.load(open(t['source_bank_json']))
    source=sorted(mgr.parse_messages(source_row), key=lambda x:int(x.get('MESSAGE_ID') or 0))
    mism=[]; fixed=[]
    for i,m in enumerate(current,1):
        expected=link(source[i-1]) if i-1<len(source) else ''
        actual=link(m)
        if actual!=expected:
            mism.append({'message_id':i,'expected_seq':seq(expected),'actual_seq':seq(actual),'expected':expected,'actual':actual})
        x=deepcopy(m)
        x['MESSAGE_ID']=i
        x['LINK_1']=expected
        fixed.append(x)
    return current, fixed, mism

async def main():
    OUT.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
    p,browser,ctx,page,rows,headers,post_url=await mgr.capture_rows_headers()
    try:
        live={r.get('NAME'):r for r in rows}
        tracker=json.load(open(TRACKER))
        fixed_results=[]; skipped=[]
        for t in tracker['templates']:
            name=t['name']
            row=live.get(name)
            if not row:
                skipped.append({'template':name,'reason':'not found live'}); continue
            current,fixed,mism=audit_and_fix(row,t)
            if not mism:
                continue
            bpath=BACKUP/f'{safe_name(name)}-before-link-slot-fix-{stamp}.json'
            mgr.save_json(bpath,row)
            payload=deepcopy(row)
            payload['MESSAGES']=json.dumps(fixed,ensure_ascii=False,separators=(',',':'))
            resp=await ctx.request.post(post_url,headers=headers,data=json.dumps(payload,ensure_ascii=False))
            body=(await resp.text())[:250]
            if resp.status>=300:
                fixed_results.append({'template':name,'ok':False,'post_status':resp.status,'body_head':body,'mismatches_before':len(mism),'backup':str(bpath)})
                continue
            fixed_results.append({'template':name,'ok':True,'post_status':resp.status,'messages':len(fixed),'mismatches_before':len(mism),'first_bad_slots':[m['message_id'] for m in mism[:10]],'backup':str(bpath)})
        # re-read live and re-audit all tracked templates
        p2,b2,ctx2,page2,rows2,headers2,post_url2=await mgr.capture_rows_headers()
        try:
            live2={r.get('NAME'):r for r in rows2}
            remaining=[]
            for t in tracker['templates']:
                row=live2.get(t['name'])
                if not row:
                    remaining.append({'template':t['name'],'error':'not found live'}); continue
                _,_,mism=audit_and_fix(row,t)
                if mism:
                    remaining.append({'template':t['name'],'mismatches':len(mism),'first_bad_slots':[m['message_id'] for m in mism[:10]]})
        finally:
            await b2.close(); await p2.stop()
        report={'executed_at_et':dt.datetime.now(TZ).isoformat(timespec='seconds'),'fixed_count':sum(1 for r in fixed_results if r.get('ok')),'failed_count':sum(1 for r in fixed_results if not r.get('ok')),'fixed_templates':fixed_results,'skipped':skipped,'remaining_bad_count':len(remaining),'remaining_bad':remaining}
        j=OUT/f'link-slot-fix-{stamp}.json'; j.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        c=OUT/f'link-slot-fix-{stamp}.csv'
        with c.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['template','ok','messages','mismatches_before','first_bad_slots','post_status','backup'])
            w.writeheader(); w.writerows([{k:r.get(k) for k in ['template','ok','messages','mismatches_before','first_bad_slots','post_status','backup']} for r in fixed_results])
        print(json.dumps({'status':'OK' if not remaining and not report['failed_count'] else 'WARN','fixed_count':report['fixed_count'],'failed_count':report['failed_count'],'remaining_bad_count':len(remaining),'json':str(j),'csv':str(c),'fixed_templates':[r['template'] for r in fixed_results if r.get('ok')],'remaining_bad':remaining[:10]},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
