#!/usr/bin/env python3
"""Read-only destination audit for six approved Router hosts; no DNS/SSL/route/site writes."""
import concurrent.futures, hashlib, importlib.util, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests
BASE=Path('/root/mgs-agent');AUTH='1556352434480095341'
OUT=BASE/'data/mgs-router-destination-audit-1556352434480095341.json'
spec=importlib.util.spec_from_file_location('cutover',BASE/'scripts/mgs-router-cutover-eleven-dns.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def probe(url):
    try:
        r=requests.get(url,allow_redirects=True,timeout=25)
        body=r.text
        titles=re.findall(r'<title[^>]*>(.*?)</title>',body,re.I|re.S)
        canon=re.findall(r'<link\b[^>]*rel=[\"\x27]canonical[\"\x27][^>]*href=[\"\x27]([^\"\x27]+)',body,re.I)
        return {'requested':url,'http':r.status_code,'final_url':r.url,'redirects':[{'http':h.status_code,'url':h.url,'location':h.headers.get('Location')} for h in r.history],'title':re.sub(r'\s+',' ',titles[0])[:180] if titles else None,'canonical':canon[:1],'server':r.headers.get('Server'),'cf_cache_status':r.headers.get('CF-Cache-Status'),'cache_control':r.headers.get('Cache-Control'),'wordpress_markers':bool(re.search(r'wp-content|wp-json|wp-includes',body)),'body_bytes':len(r.content),'body_sha256':hashlib.sha256(r.content).hexdigest()}
    except requests.RequestException as e:return {'requested':url,'error':type(e).__name__,'http':None}

def main():
    qa=json.loads((BASE/'data/mgs-router-eleven-cutover-browser-destinations.json').read_text());hosts=qa['destination_chain_pending'];assert len(hosts)==6
    cfg=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());routes=[r for r in cfg['routes'] if r['host'] in hosts];assert len(routes)==52
    before=m.hashes();source=json.loads((BASE/'data/mgs-router-eleven-domains-keitaro-source.json').read_text());source_urls={l['destination'] for c in source['campaigns'] for st in c['streams'] for l in st['landings']}
    dest={}
    for r in routes:
        for t in r.get('destinations',[]) or ([{'url':r['destination']}] if r.get('destination') else []):
            u=t['url'];bare=u.split('?',1)[0]
            entry=dest.setdefault(bare,{'url':bare,'source_urls':[],'traffic_hosts':[],'aliases':[]})
            if u not in entry['source_urls']:entry['source_urls'].append(u)
            if r['host'] not in entry['traffic_hosts']:entry['traffic_hosts'].append(r['host'])
            alias={'host':r['host'],'path':r['path']}
            if alias not in entry['aliases']:entry['aliases'].append(alias)
            assert u in source_urls,'destination_not_saved_source'
    report={'authorization_message_id':AUTH,'started_at':m.now(),'scope_hosts':hosts,'scope_routes':len(routes),'unique_destination_paths':len(dest),'status':'in_progress','immutable_before':before,'scope':'read_only; no route DNS SSL WordPress mutations','checks':[]}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for bare,result in zip(dest,pool.map(probe,dest)):
            row=dest[bare];row['public_bare']=result;row['public_with_source_query']=probe(m.resolve(row['source_urls'][0],m.RAW))
            report['checks'].append(row)
            OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    health_hosts=sorted({urlsplit(u).hostname for u in dest})
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:report['host_health']=list(pool.map(probe,['https://'+h+'/' for h in health_hosts]))
    totals={}
    for row in report['checks']:
        key=str(row['public_bare']['http']);totals[key]=totals.get(key,0)+1
    report['HTTP_totals']=totals;report['immutable_after']=m.hashes();assert before==report['immutable_after'];report['status']='public_destination_audit_complete';report['completed_at']=m.now()
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'scope_routes':len(routes),'unique_destination_paths':len(dest),'totals':totals,'host_health':[{'host':urlsplit(x['requested']).hostname,'http':x['http'],'title':x.get('title')} for x in report['host_health']],'Router_immutable_unchanged':True,'artifact':str(OUT)},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
