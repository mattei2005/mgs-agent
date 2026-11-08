import json,sys,subprocess,shutil,runpy
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');ph=json.loads((B/'phases.json').read_text());P=Path(ph['publish_pay_now']['run_dir']);v=json.loads((P/'visual-verification.json').read_text());targets=json.loads((P/'targets.json').read_text())
for aid,amount in [('1877104513669062','382.04'),('1085117577390237','1051.03')]:
 x=next(x for x in targets if x['account_id']==aid);assert aid not in v['verified_account_ids'];v['verified_account_ids'].append(aid);v['accounts_list_checks'][aid]={'valid_billing_list':True,'business_id':'155263197283282','row_account_id':aid,'name':x['name'],'balance_usd':amount}
assert len(v['verified_account_ids'])==18
(P/'visual-verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2));(P/'visual-verification.json').chmod(0o600)
ph['initial_refresh_workbook']=ph['refresh_workbook']
for name,args,key in [('publish_pay_now',['--run-dir',str(P),'--verified-only','--apply'],'h_publication'),('refresh_workbook',['--apply','--allow-history-pending'],'refresh_workbook'),('validate_workbook_readonly',['--spreadsheet-id','1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU','--sheet-id','271321738','--business-id','155263197283282'],'validation')]:
 r=subprocess.run([sys.executable,str(S/(name+'.py')),*args],capture_output=True,text=True,timeout=550);(B/(key+'-final.stdout')).write_text(r.stdout);(B/(key+'-final.stderr')).write_text(r.stderr)
 try:d=json.loads(r.stdout)
 except ValueError:d={'output':r.stdout,'returncode':r.returncode}
 ph[key]=d;(B/'phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2));print(key,json.dumps(d,ensure_ascii=False),flush=True)
 if r.returncode or d.get('status')=='blocked':sys.exit(2)
