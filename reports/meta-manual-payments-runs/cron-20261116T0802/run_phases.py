import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
p={'scheduled_at':'2026-11-16T08:02:00-05:00','completed':{}}
assert not (R/'progress.json').exists(),'reconcile_existing_progress'
for name,script,args in [('funding','regroup_funding.py',['--apply']),('invoices','refresh_september_invoices.py',['--apply']),('api','refresh_workbook.py',['--apply','--allow-history-pending']),('h_prepare','publish_pay_now.py',['--prepare'])]:
 q=subprocess.run([sys.executable,str(R/'launch.py'),str(S/script),*args],text=True,capture_output=True,timeout=300)
 (R/(name+'.log')).write_text(q.stdout+'\n'+q.stderr)
 try: data=json.loads(q.stdout)
 except Exception: data=json.loads(q.stdout.strip().splitlines()[-1])
 p['completed'][name]={'returncode':q.returncode,'stdout':json.dumps(data,ensure_ascii=False)}
 (R/'progress.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
 print(json.dumps({'phase':name,'rc':q.returncode,'result':data},ensure_ascii=False),flush=True)
 assert q.returncode==0,(name,'failed')
