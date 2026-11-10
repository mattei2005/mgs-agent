import json,sys,subprocess,shutil,re
from pathlib import Path
B=Path(__file__).parent;S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
launcher=Path(shutil.which('hermes')).resolve();py=re.search(r'^exec (\S+)',launcher.read_text(),re.M)[1];run='/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261109T1402/run.py'
assert (B/'baseline.json').is_file();ph={}
for name,args in [('regroup_funding',['--apply']),('refresh_september_invoices',['--apply']),('refresh_workbook',['--apply','--allow-history-pending']),('publish_pay_now',['--prepare'])]:
 r=subprocess.run([py,run,str(S/(name+'.py'))]+args,capture_output=True,text=True,timeout=260)
 (B/(name+'-stdout.txt')).write_text(r.stdout);(B/(name+'-stderr.txt')).write_text(r.stderr)
 d=json.loads(r.stdout.strip().splitlines()[-1]);ph[name]=d;(B/'phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2));print(name,json.dumps(d,ensure_ascii=False),flush=True);assert r.returncode==0 and d.get('status')!='blocked'
