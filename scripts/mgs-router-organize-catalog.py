#!/usr/bin/env python3
"""Add catalog/group metadata to existing Wantabrand routes, preserving traffic semantics."""
import argparse, copy, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests

BASE=Path('/root/mgs-agent')
URL='https://route.mgsdigitalcorp.com'
APPROVAL='1555778254592417816'
PLAN=BASE/'data/mgs-router-catalog-plan.json'
RESULT=BASE/'data/mgs-router-catalog-migration-validation.json'
BACKUP=Path('/root/.local/share/mgs-router-rollbacks')/APPROVAL

def semantic(routes):
    return [{k:v for k,v in r.items() if k not in ('group','destination_id')} | ({'destinations':[{k:v for k,v in t.items() if k!='destination_id'} for t in r['destinations']]} if 'destinations' in r else {}) for r in routes]

def build(current):
    source=json.loads((BASE/'data/mgs-router-wantabrand-keitaro-source.json').read_text())
    expected=json.loads((BASE/'data/mgs-router-wantabrand-import-plan.json').read_text())['routes']
    bykey=lambda rows:{(r['host'],r['path']):r for r in rows}
    if bykey(semantic(current['routes']))!=bykey(expected):raise RuntimeError('route_semantics_changed_since_authorized_source')
    next=copy.deepcopy(current); catalog={}; groups=set(); landing_groups={}
    for c in source['campaigns']:
        group=c['name'].split(' - ')[0]; groups.add(group)
        host=urlsplit(c['domain']).hostname; route=bykey(next['routes'])[(host,'/'+c['alias'])]
        route['group']=group
        landings=c['streams'][0]['landings']
        for i,l in enumerate(landings):
            id='ktr-'+str(l['id']); d={'id':id,'name':l['name'],'url':l['destination']}
            if id in catalog and catalog[id]!=d:raise RuntimeError('source_landing_metadata_conflict')
            catalog[id]=d;landing_groups.setdefault(id,set()).add(group)
            if 'destinations' in route:
                if route['destinations'][i]['url']!=d['url']:raise RuntimeError('target_order_mismatch')
                route['destinations'][i]['destination_id']=id
            else:
                if route['destination']!=d['url']:raise RuntimeError('single_destination_mismatch')
                route['destination_id']=id
    for id,d in catalog.items():
        gs=landing_groups[id];d['group']=sorted(gs)[0] if len(gs)==1 else ''
    next['catalog']=sorted(catalog.values(),key=lambda d:d['id']);next['groups']=sorted(groups)
    if semantic(next['routes'])!=semantic(current['routes']):raise RuntimeError('migration_changes_redirects')
    # An exact previous catalog is an idempotent no-op, not a second write.
    if current.get('catalog') and current!=next:raise RuntimeError('existing_catalog_conflict_preserved')
    return next

def login():
    p=subprocess.run([str(BASE/'scripts/mgs-op-with-service-account.sh'),'item','get','MGS Router - Rodolfo','--vault','MGS Conteúdo','--format','json','--reveal'],capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError('canonical_1Password_login_unavailable')
    item=json.loads(p.stdout);fields={x.get('id'):x.get('value') for x in item['fields']}
    s=requests.Session();r=s.post(URL+'/login',data={'username':fields['username'],'password':fields['password']},headers={'Origin':URL},allow_redirects=False,timeout=30)
    if r.status_code!=303 or r.headers.get('Location')!='/admin':raise RuntimeError('panel_login_failed')
    me=s.get(URL+'/api/me',timeout=30);me.raise_for_status()
    return s,{'Origin':URL,'X-CSRF-Token':me.json()['csrf']}

def read(s):
    r=s.get(URL+'/api/routes',timeout=30);r.raise_for_status();return r.json()

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--approval-message-id');args=p.parse_args()
    if args.apply and args.approval_message_id!=APPROVAL:raise RuntimeError('exact_approval_message_required')
    if not args.apply:
        current=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());next=build(current)
        PLAN.write_text(json.dumps(next,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':'plan_validated','routes':len(next['routes']),'catalog':len(next['catalog']),'groups':next['groups'],'redirects_unchanged':True,'live_writes':0}));return
    if not (BACKUP/'mgs-router').exists() or not (BACKUP/'routes.json').exists():raise RuntimeError('rollback_backup_required')
    s,headers=login();writes=0
    try:
        before=read(s);next=build(before)
        if before!=next:
            try:r=s.post(URL+'/api/routes',json=next,headers=headers,timeout=30)
            except requests.RequestException:
                after=read(s);wanted={**next,'revision':before['revision']+1}
                if after!=wanted:raise RuntimeError('write_outcome_unconfirmed_no_retry')
            else:
                if r.status_code!=200:raise RuntimeError('catalog_write_rejected_'+str(r.status_code))
                writes=1
        after=read(s);wanted={**next,'revision':before['revision']+(before!=next)}
        if after!=wanted:raise RuntimeError('catalog_readback_mismatch')
        if semantic(before['routes'])!=semantic(after['routes']):raise RuntimeError('traffic_semantics_changed')
        report={'status':'catalog_migration_readback_passed','authorization_message_id':APPROVAL,'revision':after['revision'],'routes':len(after['routes']),'destination_entries':sum(len(r.get('destinations',[])) or 1 for r in after['routes']),'catalog_destinations':len(after['catalog']),'groups':after['groups'],'route_API_writes':writes,'redirects_names_aliases_URLs_weights_unchanged':True,'DNS_Keitaro_DTR_SB_writes':0,'secrets_emitted':False,'validated_at':datetime.now(timezone.utc).isoformat()}
        RESULT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
    finally:
        r=s.post(URL+'/logout',json={},headers=headers,timeout=30)
        if r.status_code!=200:raise RuntimeError('logout_failed')
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'failed','error':str(e) if isinstance(e,RuntimeError) else type(e).__name__,'secrets_emitted':False}));sys.exit(1)
