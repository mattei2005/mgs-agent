import sys,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
L='/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261115T0802/launch.py'
p={'scheduled_at':'2026-11-18T08:02:00-05:00','completed':{}}
assert (R/'workbook-before.json').exists() and not(R/'progress.json').exists()
for phase,args in [('funding',['regroup_funding.py','--apply']),('invoices',['refresh_september_invoices.py','--apply']),('api',['refresh_workbook.py','--apply','--allow-history-pending']),('h_prepare',['publish_pay_now.py','--prepare'])]:
 x=subprocess.run([sys.executable,L,str(S/args[0]),*args[1:]],capture_output=True,text=True,timeout=520)
 (R/(phase+'.log')).write_text(x.stdout+'\n'+x.stderr)
 assert x.returncode==0,(phase,x.returncode,x.stdout[-800:])
 d=json.loads(x.stdout);assert d.get('status') not in ['blocked','error'],d
 p['completed'][phase]={'stdout':x.stdout,'returncode':x.returncode}
 (R/'progress.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
 print(json.dumps({'phase':phase,'result':d},ensure_ascii=False),flush=True)
