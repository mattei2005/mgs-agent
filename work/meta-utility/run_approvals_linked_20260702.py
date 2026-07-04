#!/usr/bin/env python3
import asyncio,json,csv,pathlib,datetime as dt,collections,importlib.util
from zoneinfo import ZoneInfo
BASE=pathlib.Path('/root/mgs-agent')
TRACK=BASE/'data/sb-utility-rollout-tracker.json'
OUT=BASE/'work/meta-utility/run-approvals-linked-20260702'; OUT.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo('America/New_York')
spec=importlib.util.spec_from_file_location('mgr', BASE/'scripts/sb-utility-rollout-manager.py')
mgr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mgr)

def status_of(m):
    if int(m.get('INVALID_FORMAT') or 0)>0: return 'INVALID'
    if int(m.get('REJECTED') or 0)>0: return 'REJECTED'
    if int(m.get('ERROR') or 0)>0: return 'ERROR'
    if int(m.get('APPROVED') or 0)>0: return 'APPROVED'
    return 'GRAY'

def motivo(msgs):
    c=collections.Counter(status_of(m) for m in msgs)
    bad=c['REJECTED']+c['ERROR']+c['INVALID']
    parts=[]
    if bad: parts.append('bad='+str(bad)+' '+ '/'.join(f'{k}={c[k]}' for k in ['REJECTED','ERROR','INVALID'] if c[k]))
    if c['GRAY']: parts.append(f"gray={c['GRAY']}")
    if c['APPROVED']: parts.append(f"approved={c['APPROVED']}")
    return ' | '.join(parts) if parts else '-'

def fmt_eta(seconds):
    if seconds <= 0: return 'sem página'
    m,s=divmod(seconds,60); h,m=divmod(m,60)
    if h: return f'{h}h{m:02d}m'
    if m: return f'{m}m{s:02d}s' if s else f'{m}m'
    return f'{s}s'

async def main():
    p,b,ctx,page,rows,headers,post_url=await mgr.capture_rows_headers()
    try:
        tracked={t['name'] for t in json.load(open(TRACK))['templates']}
        live=[]
        for r in rows:
            n=r.get('NAME')
            if n not in tracked: continue
            pages=int(r.get('PAGES') or 0); msgs=mgr.parse_messages(r)
            if pages>0:
                live.append({'template':n,'id':r.get('ID'),'pages':pages,'msgs':len(msgs),'motivo':motivo(msgs)})
        live.sort(key=lambda x:x['template'].lower())
        approvals=[]
        for x in live:
            url=f'https://api.jbfdigital.com.br/broadcast/Messenger/{x["id"]}/approve'
            resp=await ctx.request.post(url,headers=headers,data='{}')
            body=(await resp.text())[:300]
            x['run_approval_status']=resp.status
            x['run_approval_ok']=200 <= resp.status < 300
            x['run_approval_body_head']=body
            x['eta_seconds']=x['pages']*x['msgs']*8
            x['eta']=fmt_eta(x['eta_seconds'])
            approvals.append(x)
        stamp=dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
        jp=OUT/f'run-approvals-linked-{stamp}.json'; jp.write_text(json.dumps({'executed_at_et':dt.datetime.now(TZ).isoformat(timespec='seconds'),'count':len(approvals),'approvals_ok':sum(1 for x in approvals if x['run_approval_ok']),'rows':approvals},ensure_ascii=False,indent=2))
        cp=OUT/f'run-approvals-linked-{stamp}.csv'
        with cp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['template','pages','msgs','motivo','eta','eta_seconds','run_approval_ok','run_approval_status'])
            w.writeheader(); w.writerows([{k:x.get(k) for k in w.fieldnames} for x in approvals])
        max_eta=max((x['eta_seconds'] for x in approvals), default=0)
        print(json.dumps({'status':'OK' if all(x['run_approval_ok'] for x in approvals) else 'WARN','count':len(approvals),'approvals_ok':sum(1 for x in approvals if x['run_approval_ok']),'total_pages':sum(x['pages'] for x in approvals),'max_eta':fmt_eta(max_eta),'json':str(jp),'csv':str(cp)},ensure_ascii=False))
        print('---ROWS---')
        for x in approvals:
            print(f"{x['template']}\t{x['pages']}\t{x['msgs']}\t{x['motivo']}\t{x['eta']}\t{x['run_approval_status']}")
    finally:
        await b.close(); await p.stop()
asyncio.run(main())
