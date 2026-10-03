#!/usr/bin/env python3
"""Read-only HTTP parity checks against the owner's exact saved Keitaro scope."""
import json,concurrent.futures
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import parse_qsl,quote_plus
import requests
BASE=Path('/root/mgs-agent')
RAW='utm_source=face%62ook&utm_medium=A+B&utm_campaign=x%26y%3Dz&utm_term=~&utm_content=A%2BB&fbclid=a%2Fb&x=1&x=2'
def resolve(u,raw):
 for k,v in dict(parse_qsl(raw,keep_blank_values=True)).items():
  if k in ['utm_source','utm_medium','utm_campaign','utm_term','utm_content']:
   encoded=quote_plus(v).replace('~','%7E');u=u.replace('{'+k+'}',encoded).replace(quote_plus('{'+k+'}'),encoded)
 return u

def check(c):
 lands=c['streams'][0]['landings'];allowed={resolve(l['destination'],RAW) for l in lands}
 url=c['domain'].rstrip('/')+'/'+c['alias']+'?'+RAW
 attempts=[]
 for attempt in range(2):
  try:
   r=requests.get(url,allow_redirects=False,timeout=25)
   ok=(r.status_code==302 and r.headers.get('Location') in allowed) if lands else (r.status_code==500 and not r.headers.get('Location'))
   attempts.append({'http':r.status_code,'matches':ok})
   if ok:break
  except requests.RequestException as e:attempts.append({'error':type(e).__name__,'matches':False})
 return {'id':c['id'],'alias':c['alias'],'host':c['domain'],'source_status_expected':302 if lands else 500,'matches':attempts[-1]['matches'],'attempts':attempts}
def main():
 s=json.loads((BASE/'data/mgs-router-eleven-domains-keitaro-source.json').read_text());cs=s['campaigns'];assert len(cs)==428
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(check,cs))
 rows.sort(key=lambda r:r['id']);assert len({r['id'] for r in rows})==428
 d={'checked_at':datetime.now(timezone.utc).isoformat(),'source_routes':len(rows),'failed':[r for r in rows if not r['matches']],'checks':rows,'DNS_writes':0,'Keitaro_writes':0,'query_semantics':'PHP-urlencoded present UTM substitutions only; last duplicate wins; extras not passed; missing macros retained'}
 (BASE/'data/mgs-router-eleven-source-live-parity.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k!='checks'},ensure_ascii=False))
 if d['failed']:raise SystemExit(1)
if __name__=='__main__':main()
