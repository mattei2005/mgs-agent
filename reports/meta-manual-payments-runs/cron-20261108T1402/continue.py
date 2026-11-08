import sys,json,subprocess,shutil
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
ph=json.loads((B/'phases.json').read_text())
r=subprocess.run([sys.executable,str(S/'publish_pay_now.py'),'--prepare'],capture_output=True,text=True,timeout=180)
(B/'publish_pay_now-recovered-stdout.txt').write_text(r.stdout);(B/'publish_pay_now-recovered-stderr.txt').write_text(r.stderr)
assert r.returncode==0,r.stderr
ph['publish_pay_now']=json.loads(r.stdout);(B/'phases.json').write_text(json.dumps(ph,ensure_ascii=False,indent=2));print(r.stdout,flush=True)
P=Path(ph['publish_pay_now']['run_dir']);ids=[x['account_id']for x in json.loads((P/'targets.json').read_text())[:6]]
r=subprocess.run([sys.executable,str(S/'read_pc1_accounts_list.py'),'--run-dir',str(P),'--account-ids',*ids],capture_output=True,text=True,timeout=300)
(B/'batch1.log').write_text(r.stdout+'\n'+r.stderr);print(r.stdout,flush=True);print('batch_returncode',r.returncode)
