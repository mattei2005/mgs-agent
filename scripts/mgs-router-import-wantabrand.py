#!/usr/bin/env python3
"""Import the approved Wantabrand routes only; never change DNS or Keitaro."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
import requests

BASE=Path('/root/mgs-agent')
SOURCE=BASE/'data/mgs-router-wantabrand-keitaro-source.json'
PLAN=BASE/'data/mgs-router-wantabrand-import-plan.json'
RESULT=BASE/'data/mgs-router-wantabrand-import-validation.json'
URL='https://route.mgsdigitalcorp.com'
APPROVAL='1555703152307740803'

def expected_routes():
    source=json.loads(SOURCE.read_text());campaigns=source['campaigns']
    assert len(campaigns)==len({c['id'] for c in campaigns})==source['campaign_count']==41
    routes=[]
    for c in sorted(campaigns,key=lambda x:x['id']):
        d=urlsplit(c['domain'])
        assert d.scheme=='https' and d.hostname in ('card.wantabrand.com','tarjeta.wantabrand.com') and d.path=='/' and not d.query and not d.fragment and not d.username and d.port is None
        assert c['state']=='active' and c['type']=='position' and re.fullmatch(r'[A-Za-z0-9_-]+',c['alias'])
        assert len(c['streams'])==1
        s=c['streams'][0]
        assert s['state']=='active' and s['schema']=='landings' and s['type']=='regular' and not s['filters'] and not s['offers']
        targets=[]
        for l in s['landings']:
            assert l['state']=='active' and l['action_type']=='http' and l['landing_type']=='external' and isinstance(l['share'],int) and 0<l['share']<=100
            targets.append({'url':l['destination'],'weight':l['share']})
        assert targets and sum(t['weight'] for t in targets)==100
        r={'host':d.hostname,'path':'/'+c['alias'],'name':c['name']}
        if len(targets)==1:r['destination']=targets[0]['url']
        else:r['destinations']=targets
        routes.append(r)
    assert len({(r['host'],r['path']) for r in routes})==41
    return routes

def login():
    p=subprocess.run(['op','item','get','MGS Router - Rodolfo','--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--format','json','--reveal'],capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError('1Password_login_unavailable')
    item=json.loads(p.stdout);f={x.get('id'):x.get('value') for x in item['fields']}
    s=requests.Session()
    response=s.post(URL+'/login',data={'username':f['username'],'password':f['password']},headers={'Origin':URL},allow_redirects=False,timeout=30)
    if response.status_code!=303 or response.headers.get('Location')!='/admin':raise RuntimeError('panel_login_failed')
    me=s.get(URL+'/api/me',timeout=30);me.raise_for_status()
    return s,{'Origin':URL,'X-CSRF-Token':me.json()['csrf']}

def merge(current,expected):
    existing={(r['host'],r['path']):r for r in current['routes']};added=0;routes=list(current['routes'])
    for r in expected:
        key=(r['host'],r['path'])
        if key in existing:
            if existing[key]!=r:raise RuntimeError('existing_route_conflict_preserved')
        else:routes.append(r);added+=1
    return {'revision':current['revision'],'routes':routes},added

def read_config(s):
    r=s.get(URL+'/api/routes',timeout=30);r.raise_for_status();return r.json()

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--verify-only',action='store_true');p.add_argument('--approval-message-id');args=p.parse_args()
    expected=expected_routes()
    if args.apply and args.approval_message_id!=APPROVAL:raise RuntimeError('exact_approval_message_required')
    if not args.apply and not args.verify_only:
        PLAN.write_text(json.dumps({'revision':0,'routes':expected},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':'plan_validated','routes':len(expected),'domains':sorted({r['host'] for r in expected}),'destinations':sum(len(r.get('destinations',[])) or 1 for r in expected),'live_writes':0}));return
    s,headers=login();writes=0;added=0
    try:
        before=read_config(s)
        if args.apply:
            for attempt in range(3):
                current=read_config(s);payload,added=merge(current,expected)
                if not added:break
                try:r=s.post(URL+'/api/routes',json=payload,headers=headers,timeout=30)
                except requests.RequestException:
                    reconciled=read_config(s)
                    if merge(reconciled,expected)[1]==0:break
                    raise RuntimeError('write_outcome_unconfirmed_readback_does_not_prove_complete')
                if r.status_code==409:continue
                if r.status_code!=200:raise RuntimeError('route_write_rejected_'+str(r.status_code))
                writes+=1;break
            else:raise RuntimeError('configuration_concurrency_gate')
        after=read_config(s);existing={(r['host'],r['path']):r for r in after['routes']}
        assert all(existing.get((r['host'],r['path']))==r for r in expected)
        assert all(existing.get((r['host'],r['path']))==r for r in before['routes'])
        report={'status':'all_41_routes_read_back_exactly','approval_message_id':APPROVAL,'routes_imported':len(expected),'destinations':sum(len(r.get('destinations',[])) or 1 for r in expected),'total_route_count':len(after['routes']),'revision':after['revision'],'route_API_writes_this_run':writes,'routes_added_this_run':added,'previous_routes_preserved':True,'names_aliases_URLs_weights_identical':True,'DNS_Keitaro_DTR_SB_writes':0,'traffic_DNS_cutover':False,'secrets_emitted':False,'validated_at':datetime.now(timezone.utc).isoformat()}
        if args.apply:RESULT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))
    finally:
        r=s.post(URL+'/logout',json={},headers=headers,timeout=30)
        if r.status_code!=200:raise RuntimeError('panel_logout_failed')
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'failed','error':str(e) if isinstance(e,RuntimeError) else type(e).__name__,'secrets_emitted':False}));sys.exit(1)
