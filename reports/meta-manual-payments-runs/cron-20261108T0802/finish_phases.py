import json,sys,subprocess,shutil
from pathlib import Path
launcher=shutil.which('hermes');assert launcher
R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');ph=json.loads((B/'phases.json').read_text());P=Path(ph['publish_pay_now']['run_dir'])
assert (P/'blocked.png').is_file() and not list(P.glob('*-receipt.json'))
(P/'visual-verification.json').write_text(json.dumps({'verified_account_ids':[],'accounts_list_checks':{},'status':'blocked_before_first_accounts_row','reason':'facebook_twofactor_reauth','inspected_screenshot':str(P/'blocked.png')},indent=2))
(P/'visual-verification.json').chmod(0o600)
ph['h_publication']={'status':'not_applied_no_verified_rows','fresh_h_count':0,'preserved_h_count':len(json.loads((P/'targets.json').read_text())),'reason':'facebook_twofactor_reauth','sheet_writes':0}
ph['initial_refresh_workbook']=ph['refresh_workbook']
for name,args,key in [('refresh_workbook',['--apply','--allow-history-pending'],'refresh_workbook'),('validate_workbook_readonly',['--spreadsheet-id','1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU','--sheet-id','271321738','--business-id','155263197283282'],'validation')]:
 r=subprocess.run([sys.executable,str(S/(name+'.py')),*args],capture_output=True,text=True,timeout=550);(B/(key+'-final.stdout')).write_text(r.stdout);(B/(key+'-final.stderr')).write_text(r.stderr)
 try:d=json.loads(r.stdout)
 except ValueError:d={'output':r.stdout,'returncode':r.returncode}
 ph[key]=d;(B/'phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2));print(key,json.dumps(d,ensure_ascii=False),flush=True)
 if r.returncode or d.get('status')=='blocked':sys.exit(2)
