import hashlib,json,subprocess,sys
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13'
kind=sys.argv[1] if len(sys.argv)>1 else 'candidate'
old=json.loads((R/'data/ares/meta-ads/audit/maintenance/t_9700e988/installed-final-tests.json').read_text())
pertinent=[r['suite'] for r in old if r['success']]+['test_discord_authority_transport']
shared=[p.stem for p in (R/'tests').glob('test_shein*.py')]
shared+=['test_reviewed_ad_schedule','test_reviewed_copy_omissions','test_reviewed_copy_targeting']
shared=[s for s in shared if (R/'tests'/f'{s}.py').exists() and s not in pertinent]
suites=pertinent+sorted(set(shared))
files=[*(R/'scripts/ares_campaign_v3').glob('*.py'),R/'scripts/ares-eggbev-target-clone.py',R/'scripts/ares-eggbev-creation.py',*[R/'tests'/f'{s}.py' for s in suites]]
pins={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
if kind=='candidate':pins['scripts/ares_campaign_v3/shein_channel_authority.py']=hashlib.sha256((M/'shein_channel_authority.py').read_bytes()).hexdigest()
(M/(kind+'-runtime-hashes.json')).write_text(json.dumps(pins,indent=2)+'\n')
results=[]
for name in suites:
 proc=subprocess.run(['/usr/bin/python3',str(M/'offline-suite.py'),name,kind],capture_output=True,text=True,timeout=120,cwd=R)
 row=json.loads(proc.stdout);row['group']='pertinent' if name in pertinent else 'shared';results.append(row)
 if not row['success']:print(json.dumps(row),flush=True)
(M/(kind+'-tests.json')).write_text(json.dumps(results,indent=2)+'\n')
drift=[p for p,h in pins.items() if hashlib.sha256((M/'shein_channel_authority.py' if kind=='candidate' and p.endswith('/shein_channel_authority.py') else R/p).read_bytes()).hexdigest()!=h]
print(json.dumps({'kind':kind,'suites':len(results),'pertinent_tests':sum(r['tests'] for r in results if r['group']=='pertinent'),'shared_tests':sum(r['tests'] for r in results if r['group']=='shared'),'failed_suites':[r['suite'] for r in results if not r['success']],'runtime_hashes':len(pins),'drift':drift}))
sys.exit(1 if drift or any(not r['success'] and r['group']=='pertinent' for r in results) else 0)
