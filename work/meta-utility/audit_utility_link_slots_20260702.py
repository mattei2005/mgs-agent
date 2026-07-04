#!/usr/bin/env python3
import asyncio, csv, json, pathlib, re, sys, datetime as dt
from zoneinfo import ZoneInfo
import importlib.util

BASE=pathlib.Path('/root/mgs-agent')
TRACKER=BASE/'data/sb-utility-rollout-tracker.json'
OUT=BASE/'work/meta-utility/link-slot-audit-20260702'
TZ=ZoneInfo('America/New_York')
spec=importlib.util.spec_from_file_location('mgr', BASE/'scripts/sb-utility-rollout-manager.py')
mgr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mgr)

def link(m): return m.get('LINK_1') or m.get('LINK 1') or ''
def seq(u):
    m=re.search(r'(?:mct|bd|jbf|ym|av)-([0-9]{3}(?:-2)?)', u or '', re.I)
    return m.group(1) if m else ''

def audit_one(name,row,t):
    current=sorted(mgr.parse_messages(row), key=lambda x:int(x.get('MESSAGE_ID') or 0))
    source_row=json.load(open(t['source_bank_json']))
    source=sorted(mgr.parse_messages(source_row), key=lambda x:int(x.get('MESSAGE_ID') or 0))
    n=len(current)
    mism=[]
    for i,m in enumerate(current,1):
        exp=link(source[i-1]) if i-1<len(source) else ''
        got=link(m)
        if got!=exp:
            mism.append({'message_id':i,'expected_seq':seq(exp),'actual_seq':seq(got),'expected':exp,'actual':got})
    return {'template':name,'messages':n,'source_bank_count':len(source),'mismatches':len(mism),'first_mismatches':mism[:10]}

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p,browser,ctx,page,rows,headers,post_url=await mgr.capture_rows_headers()
    try:
        live={r.get('NAME'):r for r in rows}
        tracker=json.load(open(TRACKER))
        results=[]
        for t in tracker['templates']:
            name=t['name']
            if name not in live:
                results.append({'template':name,'error':'not found live'})
                continue
            results.append(audit_one(name,live[name],t))
        stamp=dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
        j=OUT/f'link-slot-audit-{stamp}.json'
        j.write_text(json.dumps(results,ensure_ascii=False,indent=2))
        c=OUT/f'link-slot-audit-{stamp}.csv'
        with c.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['template','messages','source_bank_count','mismatches','first_bad_slots'])
            w.writeheader()
            for r in results:
                slots=','.join(str(x['message_id']) for x in r.get('first_mismatches',[]))
                w.writerow({'template':r.get('template'),'messages':r.get('messages'),'source_bank_count':r.get('source_bank_count'),'mismatches':r.get('mismatches',0),'first_bad_slots':slots})
        bad=[r for r in results if r.get('mismatches',0)>0 or r.get('error')]
        print(json.dumps({'status':'OK','tracked':len(results),'bad_templates':len(bad),'json':str(j),'csv':str(c),'top_bad':[(r['template'],r.get('mismatches'),[x['message_id'] for x in r.get('first_mismatches',[])[:5]]) for r in bad[:20]]},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
