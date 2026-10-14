import json,re,pathlib,collections,hashlib
P=pathlib.Path('/root/mgs-agent/work/sb-smart-routing/openzed-cutover-1559931178050527265')
pools=json.loads((P/'live-before.json').read_text())
PRE=['boostin-us-cc-en','boostin-us-cc-es','ep-us-cc-en','ep-us-cc-es','gp-de-cc-de','gp-us-cc-en','ma-us-cc-en','ma-us-cc-es','yo-us-cc-en','yo-us-cc-es','vz-mx-cc-es','vz-us-cc-es','vz-us-cc-en']
def rows(p):return json.loads(p['ROUTES'])
def sortkey(r):
 s=r['route'].split('-drip-')[-1]
 if '-drip-' in r['route']:
  if s=='nm':return (0,1,0)
  m=re.fullmatch(r'm(\d+)-(\d+)',s);n,part=map(int,m.groups());return (0,0 if n==0 else n+1,part)
 return (1,*[int(x) for x in r['route'].split('-mct-')[1].split('-')])
source={}
for family,base in [('drip','op-us-cc-en-drip 001'),('mct','op-us-cc-en-mct 001')]:
 p=next(p for p in pools if p['DOMAIN']=='openzed' and p['NAME']==base)
 source[family]=[r['url'] for r in sorted(rows(p),key=sortkey)]
 assert len(source[family])==5 and len(set(source[family]))==5
assert set(source['drip'])==set(source['mct'])
plans=[]
for p in pools:
 rr=rows(p);sel=[r for r in rr if any(r['route'].startswith(pre+'-') for pre in PRE)]
 if not sel:continue
 assert len(sel)==len(rr),'mixed pool unexpected'
 ordered=sorted(sel,key=sortkey);family='drip' if '-drip-' in ordered[0]['route'] else 'mct'
 assign={r['route']:source[family][i%5] for i,r in enumerate(ordered)}
 out=[]
 for r in rr:
  z=dict(r);z['url']=assign[r['route']];z['jbf_operation']='';out.append(z)
 plans.append({'pool_id':p['ID'],'company':p['COMPANY'],'domain':p['DOMAIN'],'family':family,'before':p,'after':dict(p,ROUTES=json.dumps(out,ensure_ascii=False))})
assert len(plans)==26 and sum(len(rows(x['after'])) for x in plans)==609
old=json.loads(pathlib.Path('/root/mgs-agent/reports/php83-post-migration-20261014/evidence/sb-routes.json').read_text())
expected={r['route'] for r in old if any(r['route'].startswith(pre+'-') for pre in PRE)}
actual={r['route'] for x in plans for r in rows(x['after'])};assert actual==expected and len(actual)==609
plan={'authorization_message_id':'1559931178050527265','scope':'Only groups A and Vizioid B/C; preserve IDs/names/metadata/topology/route/utm_content/freeze; only URL and corresponding operation replacement. No Fincgriffin or isolated case writes.','source_urls':source,'operations_resolution':'No matching Openzed destinations in source-publisher live catalog; use blank operation per explicit-URL-write exception, do not transport Openzed operation to other publisher; AdOps pending.','plans':plans}
f=P/'plan.json';f.write_text(json.dumps(plan,ensure_ascii=False,indent=2));f.chmod(0o600)
print(json.dumps({'pools':len(plans),'routes':len(actual),'source_urls':source,'routes_by_domain':dict(collections.Counter(x['domain'] for z in plans for x in [z]*len(rows(z['after'])))),'blank_operations':609,'plan_sha256':hashlib.sha256(f.read_bytes()).hexdigest()},ensure_ascii=False))
