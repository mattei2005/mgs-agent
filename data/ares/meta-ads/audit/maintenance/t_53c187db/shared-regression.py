"""Offline comparator only: preserve prior shared failures, no relaxed tests."""
import json,re,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
old=json.loads((R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13/installed-tests.json').read_text())
suites=[r['suite'] for r in old if r['group']=='shared']
def run(pair):
 kind,name=pair
 p=subprocess.run(['/usr/bin/python3',str(M/'offline-suite.py'),name,kind],capture_output=True,text=True,timeout=180,cwd=R)
 try:v=json.loads(p.stdout)
 except Exception:v={'suite':name,'tests':0,'success':False,'errors':[p.stderr[-2000:]],'failures':[]}
 return kind,v
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,[(k,s) for k in ['baseline','candidate'] for s in suites]))
results={k:[r for kind,r in rows if kind==k] for k in ['baseline','candidate']}
normalize=lambda x:re.sub(r'0x[0-9a-fA-F]+','0xADDRESS',json.dumps(x,sort_keys=True))
drift=[a['suite'] for a,b in zip(results['baseline'],results['candidate']) if normalize(a)!=normalize(b)]
summary={'suites':len(suites),'tests_baseline':sum(r['tests'] for r in results['baseline']),'tests_candidate':sum(r['tests'] for r in results['candidate']),'baseline_failed_suites':[r['suite'] for r in results['baseline'] if not r['success']],'drift':drift,'results':results}
(M/'shared-regression.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'}));sys.exit(bool(drift))
