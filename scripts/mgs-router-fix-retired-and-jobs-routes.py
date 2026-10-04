#!/usr/bin/env python3
"""Approved route retirement + thirteen exact jobs URL replacements; no DNS/SSL/site writes."""
import argparse, copy, concurrent.futures, hashlib, importlib.util, json, os, shutil, subprocess
from pathlib import Path
from urllib.parse import urlsplit
import requests
B=Path('/root/mgs-agent');AUTH='1556362463413276675';THREAD='1555381168894115912'
BACK=Path('/root/.local/share/mgs-router-rollbacks')/AUTH
OUT=B/'data/mgs-router-destination-fix-1556362463413276675.json'
DEAD={'es.conectageral.com','es.portalrelevante.com'}
REMOVE={('tarjeta.conectageral.com','/tarjetaescg'),('tarjeta.portalrelevante.com','/tarjetaespr')}
JOB=('job.conectageral.com','/artigosjobs')
spec=importlib.util.spec_from_file_location('m',B/'scripts/mgs-router-cutover-eleven-dns.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def audit(action,**extra):
    with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':action,'authorization_message_id':AUTH,'thread_id':THREAD,**extra},ensure_ascii=False)+'\n')
def save(d):OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def urls(r):return [t['url'] for t in r.get('destinations',[])] or ([r['destination']] if r.get('destination') else [])
def read(s):
    r=s.get(m.PANEL+'/api/routes',timeout=30);r.raise_for_status();return r.json()
def desired(before):
    out=copy.deepcopy(before);removed=[r for r in before['routes'] if (r['host'],r['path']) in REMOVE]
    assert len(removed)==2 and all(len(urls(r))==15 and all(urlsplit(u).hostname in DEAD for u in urls(r)) for r in removed),'retired_route_scope_drift'
    affected=[r for r in before['routes'] if any(urlsplit(u).hostname in DEAD for u in urls(r))]
    assert {(r['host'],r['path']) for r in affected}==REMOVE,'additional_retired_routes_need_scope_reconciliation'
    out['routes']=[r for r in out['routes'] if (r['host'],r['path']) not in REMOVE]
    job=next(r for r in out['routes'] if (r['host'],r['path'])==JOB);assert len(job['destinations'])==13
    candidates=json.loads((B/'data/mgs-router-destination-audit-url-candidates.json').read_text())['verified_exact_slug_candidates']
    mapping={x['old_url']:x['published_current_link'] for x in candidates if x['HTTP']==200 and x['status']=='publish' and x['traffic_hosts']==[JOB[0]]}
    assert len(mapping)==13
    ids={t['destination_id'] for t in job['destinations']};changes=[]
    assert all((r['host'],r['path'])==JOB for r in before['routes'] if any(t.get('destination_id') in ids for t in r.get('destinations',[]))),'shared_catalog_scope_changed'
    for t in job['destinations']:
        old=t['url'];parts=urlsplit(old);bare=old.split('?',1)[0];newbare=mapping[bare]
        assert parts.hostname=='conectageral.com' and parts.path.startswith('/en/') and urlsplit(newbare).hostname=='jobs.conectageral.com'
        assert urlsplit(newbare).path==parts.path.removeprefix('/en'),'exact_slug_path_drift'
        new=newbare+('?' +old.split('?',1)[1] if '?' in old else '')
        t['url']=new
        cat=next(d for d in out['catalog'] if d['id']==t['destination_id']);assert cat['url']==old;cat['url']=new
        changes.append({'destination_id':t['destination_id'],'old':old,'new':new,'weight':t['weight']})
    assert len(out['routes'])==len(before['routes'])-2 and len(out['catalog'])==len(before['catalog']) and out['groups']==before['groups']
    assert all(r in out['routes'] for r in before['routes'] if (r['host'],r['path']) not in REMOVE|{JOB})
    oldjob=next(r for r in before['routes'] if (r['host'],r['path'])==JOB)
    assert {k:v for k,v in oldjob.items() if k!='destinations'}=={k:v for k,v in job.items() if k!='destinations'}
    assert [{k:v for k,v in t.items() if k!='url'} for t in oldjob['destinations']]==[{k:v for k,v in t.items() if k!='url'} for t in job['destinations']]
    assert all(d in out['catalog'] for d in before['catalog'] if d['id'] not in ids)
    return out,removed,changes

def pages(changes):
    def check(x):
        r=requests.get(x['new'],timeout=25);return {'destination_id':x['destination_id'],'HTTP':r.status_code,'expected_url':x['new'],'final_url':r.url,'query_unchanged':urlsplit(r.url).query==urlsplit(x['new']).query}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,changes))
    assert len(rows)==13 and all(x['HTTP']==200 and x['query_unchanged'] for x in rows),'new_destination_not_HTTP200_with_original_query'
    return rows

def validation(config,changes):
    checks=m.sweep(config['routes']);failures=[x for x in checks if not x['passed']]
    retired=[]
    for host,path in sorted(REMOVE):
        for meth in ['GET','HEAD']:
            r=requests.request(meth,'https://'+host+path,allow_redirects=False,timeout=25)
            retired.append({'host':host,'path':path,'method':meth,'HTTP':r.status_code,'passed':r.status_code==404 and r.headers.get('Cache-Control')=='no-store' and r.headers.get('Referrer-Policy')=='no-referrer'})
    assert not failures and all(x['passed'] for x in retired),'live_redirect_regression'
    job=next(r for r in config['routes'] if (r['host'],r['path'])==JOB);allowed={t['url'] for t in job['destinations']};observed=set();sample=[]
    for n in range(160):
        for method in ['GET','HEAD']:
            r=requests.request(method,'https://'+JOB[0]+JOB[1]+'?'+m.RAW,allow_redirects=False,timeout=25);loc=r.headers.get('Location')
            assert r.status_code==302 and loc in allowed and r.headers.get('Cache-Control')=='no-store' and r.headers.get('Referrer-Policy')=='no-referrer','job_route_redirect_changed'
            observed.add(loc);sample.append({'method':method,'HTTP':r.status_code,'destination_id':next(t['destination_id'] for t in job['destinations'] if t['url']==loc)})
        if observed==allowed:break
    assert observed==allowed,'not_all_weighted_choices_observed'
    return {'all_routes_checks':checks,'retired_route_checks':retired,'job_route_samples':sample,'job_distinct_targets_observed':len(observed),'destination_checks':pages(changes),'all_other_routes_preserved':True,'raw_weights_sum':sum(t['weight'] for t in job['destinations']),'GET_HEAD_pass':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--approval-message-id',required=True);a=p.parse_args();assert a.approval_message_id==AUTH
    s,h=m.panel_login('MGS Router - Rodolfo')
    try:
        before=read(s);plan,removed,changes=desired(before)
        if not a.apply:
            print(json.dumps({'status':'exact_plan','routes_to_remove':[{'host':r['host'],'path':r['path']} for r in removed],'job_URL_changes':len(changes),'catalog_URL_changes':len(changes),'catalog_deletions':0,'DNS_SSL_writes':0}));return
        assert not OUT.exists(),'receipt_exists_reconcile_not_replay'
        immutable=m.hashes();BACK.mkdir(mode=0o700,parents=True,exist_ok=False)
        for n in ['routes.json','domains.json','users.json']:
            shutil.copy2('/var/lib/mgs-router/'+n,BACK/n);os.chmod(BACK/n,0o600)
        shutil.copy2('/opt/mgs-router/mgs-router',BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700)
        chk=subprocess.run([str(BACK/'mgs-router'),'--state',str(BACK),'--origin',m.PANEL,'--check'],capture_output=True,text=True,timeout=30);assert chk.returncode==0,'rollback_real_binary_rejected'
        probe=BACK/'candidate-check';probe.mkdir(mode=0o700)
        (probe/'routes.json').write_text(json.dumps(plan));os.chmod(probe/'routes.json',0o600)
        for n in ['domains.json','users.json']:shutil.copy2(BACK/n,probe/n);os.chmod(probe/n,0o600)
        chk=subprocess.run([str(BACK/'mgs-router'),'--state',str(probe),'--origin',m.PANEL,'--check'],capture_output=True,text=True,timeout=30);assert chk.returncode==0,'candidate_real_binary_rejected'
        baseline_pages=pages(changes)
        assert read(s)==before and m.hashes()==immutable,'concurrent_change_before_write'
        want=copy.deepcopy(plan);want['revision']=before['revision']+1
        d={'authorization_message_id':AUTH,'status':'ready_to_apply','before_revision':before['revision'],'after_revision':want['revision'],'removed_routes':removed,'job_changes':changes,'backup':str(BACK),'backup_and_candidate_real_binary_check':True,'pages_preflight':baseline_pages,'immutable_before':immutable,'external_writes':0,'DNS_SSL_writes':0,'WordPress_writes':0,'catalog_deletions':0,'secrets_emitted':False};save(d);audit('router_destination_fix_ready',removed_routes=[{'host':r['host'],'path':r['path']} for r in removed],job_changes=13,backup=str(BACK))
        try:
            response=s.post(m.PANEL+'/api/routes',json=plan,headers=h,timeout=40)
            if response.status_code!=200:raise RuntimeError('route_API_write_HTTP'+str(response.status_code))
        except requests.RequestException:
            if read(s)!=want:raise RuntimeError('write_ambiguous_reconciliation_required')
        after=read(s);assert after==want,'exact_route_write_readback_failed';d['external_writes']=1;d['status']='applied_exact_API_readback';save(d)
        audit('router_destination_fix_API_write_readback',revision=after['revision'],route_count=len(after['routes']),removed=2,job_URLs=13)
        try:
            d['validation']=validation(after,changes)
            assert read(s)==after,'concurrent_route_edit_after_apply'
            actual=m.hashes();assert all(actual[k]==v for k,v in immutable.items() if k!='/var/lib/mgs-router/routes.json'),'immutable_component_changed'
            assert json.loads(Path('/var/lib/mgs-router/routes.json').read_text())==after
            d.update(status='applied_validated',routes_total=len(after['routes']),catalog_total=len(after['catalog']),groups_total=len(after['groups']),validated_at=m.now(),immutable_after=actual);save(d)
            audit('router_destination_fix_validated',artifact=str(OUT),routes_total=len(after['routes']),removed_routes=2,job_destinations=13,all13_live_weighted_targets_observed=True,other_routes_catalog_groups_preserved=True)
        except Exception as error:
            current=read(s)
            if current!=after:
                d.update(status='validation_failed_rollback_blocked_by_concurrent_edit',error=type(error).__name__);save(d);raise
            rb=copy.deepcopy(before);rb['revision']=current['revision'];desired_rb=copy.deepcopy(rb);desired_rb['revision']+=1
            r=s.post(m.PANEL+'/api/routes',json=rb,headers=h,timeout=40);assert r.status_code==200 and read(s)==desired_rb,'rollback_API_failed'
            d.update(status='validation_failed_exact_state_rollback',error=str(error) if isinstance(error,(RuntimeError,AssertionError)) else type(error).__name__,rollback_revision=desired_rb['revision']);save(d);audit('router_destination_fix_rolled_back',error=d['error'],rollback_revision=desired_rb['revision']);raise
        print(json.dumps({'status':d['status'],'removed_routes':2,'job_destinations':13,'total_routes':d['routes_total'],'catalog_total':d['catalog_total'],'raw_weights_sum':d['validation']['raw_weights_sum'],'all13_targets_live_observed':True,'destination_HTTP200':len(d['validation']['destination_checks']),'redirect_checks':len(d['validation']['all_routes_checks']),'DNS_SSL_WordPress_writes':0,'artifact':str(OUT)}))
    finally:m.logout(s,h)
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
