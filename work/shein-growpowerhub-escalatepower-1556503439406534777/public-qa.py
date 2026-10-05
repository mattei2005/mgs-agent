import subprocess,json,pathlib,concurrent.futures,hashlib
W=pathlib.Path('/root/mgs-agent/work/shein-growpowerhub-escalatepower-1556503439406534777')
runtime=json.load(open(W/'final-runtime-readback.json'))
source=json.load(open(W/'runtime-before.json'))[0]
assert len(source['items'])==18 and all(i['active'] for i in source['items'] if i['layout_template'] in ('lp2','lp3'))
jobs=[]
for x in runtime:
 for slug,meta in x['static'].items():jobs.append((x['site']+'.com','/quiz/us/'+slug+'/',200,meta['sha256']))
 for m in range(1,7):jobs.append((x['site']+'.com',f'/quiz/us/sh1-g{m:03d}/',404,None))
 jobs.append((x['site']+'.com','/quiz/us/sh2-g999999/',404,None))
 for path in ['/','/rec-us-app-shein-circle-of-style/','/privacy-policy/','/terms-of-service/','/disclaimer/']:jobs.append((x['site']+'.com',path,200,None))
for i in source['items']:jobs.append(('yolokfx.com','/quiz/us/'+i['slug']+'/',200 if i['active'] else 404,None))
def run(j):
 host,path,status,sha=j
 f=W/('public-'+host+'-'+path.strip('/').replace('/','_')+'.html')
 z=subprocess.run(['curl','-sS','-L','-A','Mozilla/5.0','--max-time','45','-o',str(f),'-w','%{http_code}','https://'+host+path],text=True,capture_output=True)
 assert z.returncode==0,(host,path,z.stderr)
 actual=int(z.stdout);assert actual==status,(host,path,actual,status)
 body=f.read_bytes();h=hashlib.sha256(body).hexdigest()
 if sha:
  assert h==sha,(host,path,'public differs from physical')
  assert b'MGS Direct Quiz static' in body and b'wp-includes' not in body and b'<form' not in body and b'<input' not in body
 if status==200:assert b'Fatal error' not in body
 return {'host':host,'path':path,'status':actual,'bytes':len(body),'sha256':h,'physical_hash_matches':h==sha if sha else None}
rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(run,jobs))
assert len(rows)==len(jobs)
(W/'public-validation.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'checks':len(rows),'new_landings_200_exact_physical':sum(r['physical_hash_matches'] is True for r in rows),'v1_404':sum(r['status']==404 and '/sh1-' in r['path'] for r in rows),'unknown_404':sum('999999' in r['path'] and r['status']==404 for r in rows),'source_yolokfx_live_200':sum(r['host']=='yolokfx.com' and r['status']==200 for r in rows)}))
