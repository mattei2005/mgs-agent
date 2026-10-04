#!/usr/bin/env python3
"""Authenticated GET-only WordPress/RunCloud evidence for approved Router destination audit."""
import concurrent.futures, html, importlib.util, json
from pathlib import Path
from urllib.parse import urlsplit
import requests
B=Path('/root/mgs-agent');spec=importlib.util.spec_from_file_location('m',B/'scripts/mgs-router-cutover-eleven-dns.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OUT=B/'data/mgs-router-destination-audit-wordpress-controlplane.json'
SITES={'cliquet.com':'Wordpress - cliquet.com','openzed.com':'Wordpress - openzed.com','conectageral.com':'Zeus WordPress - conectageral.com','eggbev.com':'Zeus WordPress - eggbev.com','portalrelevante.com':'Zeus WordPress - portalrelevante.com','finanzas.conectageral.com':'Zeus WordPress - finanzas.conectageral.com','finanzas.eggbev.com':'Zeus WordPress - finanzas.eggbev.com','finanzas.portalrelevante.com':'Zeus WordPress - finanzas.portalrelevante.com','jobs.conectageral.com':'Zeus WordPress - jobs.conectageral.com'}
def catalog(job):
    host,title=job;obj=m.item(title);fields={f.get('label'):f.get('value') for f in obj['fields']}
    user=fields.get('api_auth_user') or fields.get('username');pw=fields.get('api_application_password') or fields.get('wp_app_password');assert user and pw,'app_password_missing:'+host
    if fields.get('site_domain'):assert fields['site_domain']==host
    base='https://'+host+'/wp-json/wp/v2';s=requests.Session();s.auth=(user,pw)
    out={'host':host,'credential_item':title,'GET_only':True,'types':{},'objects':[],'errors':[]}
    try:
        me=s.get(base+'/users/me',params={'_fields':'id,roles'},timeout=25)
        out['authenticated_HTTP']=me.status_code
        if me.status_code!=200:out['errors'].append({'stage':'authenticated_smoke','HTTP':me.status_code});return out
        typ=s.get(base+'/types',params={'context':'edit'},timeout=25);out['types_HTTP']=typ.status_code
        if typ.status_code!=200:return out
        types=typ.json()
        for k,v in types.items():
            if k in ['attachment','wp_block','wp_template','wp_template_part','wp_navigation','wp_global_styles','nav_menu_item','wp_font_family','wp_font_face']:continue
            rb=v.get('rest_base');ns=v.get('rest_namespace','wp/v2')
            if not rb:continue
            out['types'][k]={'rest_base':rb,'namespace':ns,'viewable':v.get('viewable')}
            page=1;expected=None;seen=[]
            while True:
                response=s.get('https://'+host+'/wp-json/'+ns+'/'+rb,params={'per_page':100,'page':page,'context':'edit','status':'publish,draft,pending,private,future','_fields':'id,slug,status,link,type,title'},timeout=30)
                if response.status_code!=200:out['errors'].append({'stage':rb,'page':page,'HTTP':response.status_code,'code':response.json().get('code') if 'json' in response.headers.get('Content-Type','') else None});break
                if expected is None:expected=int(response.headers.get('X-WP-Total','0'))
                rows=response.json();assert isinstance(rows,list)
                for x in rows:
                    title=x.get('title',{});title=title.get('raw',title.get('rendered','')) if isinstance(title,dict) else str(title)
                    seen.append({'id':x['id'],'slug':x['slug'],'status':x['status'],'link':x['link'],'type':x['type'],'title':html.unescape(title)[:250]})
                if len(seen)>=expected:break
                page+=1
            out['objects']+=seen;out['types'][k]['declared_count']=expected;out['types'][k]['collected_count']=len(seen)
            if expected is not None:assert len({x['id'] for x in seen})==expected,'catalog_count_mismatch:'+host+':'+k
        return out
    except requests.RequestException as e:out['errors'].append({'error':type(e).__name__});return out
    finally:s.close()

def runcloud():
    obj=m.item('RunCloud API - MGS');token=next(f['value'] for f in obj['fields'] if f.get('label')=='runcloud_api_key_token');s=requests.Session();s.headers.update({'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'mgs-agent-runcloud-inventory/1.0'})
    def get(p,params=None):
        r=s.get('https://manage.runcloud.io/api/v3'+p,params=params,timeout=35)
        if r.status_code!=200:raise RuntimeError('RunCloud_GET_HTTP'+str(r.status_code)+':'+p)
        return r.json()
    apps=[];page=1
    while True:
        d=get('/servers/290075/webapps',{'perPage':40,'page':page});batch=d.get('data',[]);apps+=batch
        if len(batch)<40:break
        page+=1
    wanted={'conectageral.com','eggbev.com','portalrelevante.com','es.conectageral.com','es.portalrelevante.com','jobs.conectageral.com','finanzas.conectageral.com','finanzas.eggbev.com','finanzas.portalrelevante.com'}
    out=[];all_hostnames=[]
    for app in apps:
        # Primary-name shortlist comes from the live webapp, never exposed raw (pull keys).
        name=app.get('name','')
        if not any(t in name for t in ['conectageral','portalrelevante','eggbev']):continue
        aid=app['id'];domains=get('/servers/290075/webapps/'+str(aid)+'/domains').get('data',[])
        clean=[{k:d.get(k) for k in ['id','name','type','www','redirection']} for d in domains]
        names=[d.get('name') for d in domains];all_hostnames+=names
        if not set(names)&wanted:continue
        row={'id':aid,'name':name,'root_path':app.get('rootPath',app.get('root_path')),'domains':clean}
        ssl=get('/servers/290075/webapps/'+str(aid)+'/ssl/advanced');row['advanced_ssl']={k:ssl.get(k) for k in ['advancedSSL','advancedSsl','enabled'] if k in ssl}
        out.append(row)
    return {'server_id':'290075','scoped_apps':out,'registered_es_hosts':[h for h in ['es.conectageral.com','es.portalrelevante.com'] if h in all_hostnames],'GET_only':True}

def main():
    report={'authorization_message_id':'1556352434480095341','started_at':m.now(),'status':'in_progress','WordPress':[],'external_writes':0,'secrets_emitted':False}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(catalog,SITES.items()):
            report['WordPress'].append(result);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    report['RunCloud']=runcloud();report['status']='authenticated_readonly_collection_complete';report['completed_at']=m.now();OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'sites':[{'host':x['host'],'authenticated_HTTP':x.get('authenticated_HTTP'),'objects':len(x['objects']),'errors':x['errors']} for x in report['WordPress']],'RunCloud_apps':len(report['RunCloud']['scoped_apps']),'registered_es_hosts':report['RunCloud']['registered_es_hosts'],'artifact':str(OUT)},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
