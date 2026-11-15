import hashlib,json,sys,subprocess
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_3950b5d9'
suites=[row['suite'] for row in json.loads((R/'data/ares/meta-ads/audit/maintenance/t_6dd59a8e/installed-final-tests.json').read_text()) if row['success']]+['test_target_start_revision']
files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'scripts/ares_campaign_v3').glob('*.py')}
files.update({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'scripts/ares-eggbev-target-clone.py',R/'scripts/ares-eggbev-creation.py',*[R/'tests'/f'{s}.py' for s in suites]]})
(M/'tested-runtime-hashes.json').write_text(json.dumps(files,indent=2)+'\n')
results=[]
for name in suites:
    process=subprocess.run(['/usr/bin/python3',str(M/'offline-suite.py'),name],capture_output=True,text=True,timeout=120,cwd=R)
    row=json.loads(process.stdout);results.append(row);print(json.dumps(row),flush=True)
(M/'installed-final-tests.json').write_text(json.dumps(results,indent=2)+'\n')
drift=[p for p,h in files.items() if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h]
(M/'runtime-drift.json').write_text(json.dumps(drift)+'\n')
print('TOTAL',sum(r['tests'] for r in results),'PASS',all(r['success'] for r in results),'DRIFT',drift)
sys.exit(0 if all(r['success'] for r in results) and not drift else 1)
