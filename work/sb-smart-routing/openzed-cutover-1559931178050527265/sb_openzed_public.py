import json,sys,time,pathlib,requests,concurrent.futures,collections
from urllib.parse import urlsplit,urlunsplit,urlencode,parse_qs
P=pathlib.Path('/root/mgs-agent/work/sb-smart-routing/openzed-cutover-1559931178050527265')
mode=sys.argv[1];plan=json.loads((P/'plan.json').read_text());original=pathlib.Path('/root/mgs-agent/reports/php83-post-migration-20261014/evidence')
routeinputs=json.loads((original/'routing-targets.json').read_text());byroute={r['route']:r for r in routeinputs}
params={'utm_source':'facebook','utm_medium':'g003-d','utm_campaign':'mgs_openzed_cutover','utm_content':'mgs_cutover','fbclid':'mgs_cutover_fb','gclid':'mgs_cutover_gc','mgs_audit':'1559931178050527265'}
def probe(t):
 url=t['url'];res=dict(t);attempts=[]
 for n in range(3):
  try:
   r=requests.get(url,timeout=(15,55),headers={'User-Agent':'Mozilla/5.0 (MGS route validation)','Cache-Control':'no-cache'},allow_redirects=True)
   attempts.append(r.status_code);q=parse_qs(urlsplit(r.url).query,keep_blank_values=True);expected=parse_qs(urlsplit(url).query,keep_blank_values=True)
   res.update(status=r.status_code,final_url=r.url,history=[{'status':x.status_code,'url':x.url,'location':x.headers.get('Location'),'redirector':x.headers.get('X-Redirect-By')} for x in r.history],lost=[k for k,v in expected.items() if q.get(k)!=v],bytes=len(r.content),attempts=attempts)
   if r.status_code in [429,500,502,503,504] and n<2:time.sleep(3*(n+1));continue
   return res
  except requests.RequestException as e:
   attempts.append(type(e).__name__)
   if n<2:time.sleep(2*(n+1))
   else:return dict(res,status=None,error_type=type(e).__name__,attempts=attempts)
if mode=='preflight':
 targets=[{'kind':'source','url':u+'/?'+urlencode(params)} for u in sorted(set(plan['source_urls']['drip']))]
 ids=['eb-us-cc-es-drip-m14-1','ns-us-cc-es-drip-m14-1','ly-us-cc-es-drip-m0-2','ftf-us-cc-es-mct-001','ceph-us-cc-en-drip-m1-1','ceph-us-cc-en-drip-nm','ceph-us-cc-en-mct-001-2','ceph-us-cc-en-mct-002-2']
 targets +=[dict(byroute[r],kind='isolated') for r in ids]
 targets +=[dict(byroute['cv-car-br-001'],kind='unresolved_route')]
elif mode=='residual':
 loss=json.loads((original/'parameter-loss.json').read_text());losskeys={(urlsplit(r['url']).netloc,urlsplit(r['url']).path.rstrip('/')) for r in loss if r['status']==200}
 oldhttp=[json.loads(l) for l in (original/'routing-http.jsonl').read_text().splitlines()]
 ids={'eb-us-cc-es-drip-m14-1','ns-us-cc-es-drip-m14-1','ly-us-cc-es-drip-m0-2','ftf-us-cc-es-mct-001','ceph-us-cc-en-drip-m1-1','ceph-us-cc-en-drip-nm','ceph-us-cc-en-mct-001-2','ceph-us-cc-en-mct-002-2'}
 lossi={r['route'] for r in oldhttp if r.get('location') and (urlsplit(r['location']).netloc,urlsplit(r['location']).path.rstrip('/')) in losskeys}
 targets=[dict(r,kind='fincgriffin' if r['route'].startswith(('fincg-es-cc-es-','fincg-gb-cc-en-','fincg-tr-cc-tr-')) else 'parameter_loss' if r['route'] in lossi else 'isolated') for r in routeinputs if r['route'].startswith(('fincg-es-cc-es-','fincg-gb-cc-en-','fincg-tr-cc-tr-')) or r['route'] in lossi or r['route'] in ids]
 cv=dict(byroute['cv-car-br-001'],kind='unresolved_route');cp=dict(cv['params'],utm_content='',utm_medium='g003-s');parts=urlsplit(cv['url']);cv['url']=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(cp),''));targets.append(cv)
 assert len(targets)==201
elif mode in ['canary','final']:
 plans=plan['plans'][:1] if mode=='canary' else plan['plans']
 targets=[dict(byroute[r['route']],kind='cutover',expected_url=r['url']) for p in plans for r in json.loads(p['after']['ROUTES'])]
else:raise RuntimeError('bad mode')
file=P/('public-'+mode+'.jsonl');results=[]
with file.open('w') as f,concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 for r in ex.map(probe,targets):results.append(r);f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush()
file.chmod(0o600)
if mode=='preflight':
 for r in results:print(json.dumps({k:r.get(k) for k in ['kind','route','url','status','final_url','lost']},ensure_ascii=False))
 assert all(r['status']==200 and not r['lost'] for r in results if r['kind']=='source')
elif mode=='residual':
 summary={kind:{'tested':sum(r['kind']==kind for r in results),'statuses':dict(collections.Counter(str(r.get('status')) for r in results if r['kind']==kind)),'parameter_loss':sum(bool(r.get('lost')) for r in results if r['kind']==kind)} for kind in sorted({r['kind'] for r in results})}
 (P/'residual-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
else:
 bad=[r for r in results if r.get('status')!=200 or r.get('lost') or urlsplit(r.get('final_url','')).netloc!='openzed.com' or (urlsplit(r.get('final_url','')).path.rstrip('/')!=urlsplit(r['expected_url']).path.rstrip('/'))]
 summary={'mode':mode,'tested':len(results),'http200':sum(r.get('status')==200 for r in results),'failed':len(bad),'bad':bad,'status':'PASS' if not bad else 'FAIL'}
 (P/('public-'+mode+'-summary.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False)[:15000]);assert not bad
