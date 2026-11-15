import hashlib,json,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db';kind=sys.argv[1]
old=json.loads((R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13/installed-tests.json').read_text())
pertinent=[r['suite'] for r in old if r['group']=='pertinent'];assert len(pertinent)==26 and sum(r['tests'] for r in old if r['group']=='pertinent')==519
extra=[p.stem for p in (R/'tests').glob('test*manager*storage*.py')]+[p.stem for p in (R/'tests').glob('test*asset*scope*.py')]
suites=list(dict.fromkeys(pertinent+extra+(['test_target_media_recovery'] if kind!='baseline' else [])))
files=[*(R/'scripts/ares_campaign_v3').glob('*.py'),R/'scripts/ares-eggbev-target-clone.py',*[R/'tests'/f'{s}.py' for s in suites]]
pins={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
if kind=='candidate':
 for n in ['scripts/ares-eggbev-target-clone.py','scripts/ares_campaign_v3/target_media_recovery.py']:pins[n]=hashlib.sha256((M/Path(n).name).read_bytes()).hexdigest()
(M/(kind+'-runtime-hashes.json')).write_text(json.dumps(pins,indent=2)+'\n')
def run(name):
 p=subprocess.run(['/usr/bin/python3',str(M/'offline-suite.py'),name,kind],capture_output=True,text=True,timeout=180,cwd=R)
 try:row=json.loads(p.stdout)
 except Exception:row={'suite':name,'tests':0,'success':False,'failures':[],'errors':['harness: '+p.stderr[-1000:]]}
 row['group']='pertinent' if name in pertinent else 'new' if name=='test_target_media_recovery' else 'extra';return row
with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,suites))
(M/(kind+'-tests.json')).write_text(json.dumps(results,indent=2)+'\n')
drift=[p for p,h in pins.items() if hashlib.sha256((M/Path(p).name if kind=='candidate' and p in ['scripts/ares-eggbev-target-clone.py','scripts/ares_campaign_v3/target_media_recovery.py'] else R/p).read_bytes()).hexdigest()!=h]
print(json.dumps({'kind':kind,'suites':len(results),'tests':sum(r['tests'] for r in results),'pertinent':sum(r['tests'] for r in results if r['group']=='pertinent'),'new':sum(r['tests'] for r in results if r['group']=='new'),'extra':sum(r['tests'] for r in results if r['group']=='extra'),'failed':[r for r in results if not r['success']],'drift':drift}))
