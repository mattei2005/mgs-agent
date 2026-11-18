"""Invoke only the canonical occurrence adapter; preserve supervisor custody."""
import sys,json,sqlite3,os
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_automation_supervisor import run_worker
from mgs_finance_continuity import observation,validate,CURRENT_KEY
B=Path(__file__).parent
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(CURRENT_KEY,)).fetchone());assert row['state']=='running';os.kill(int(row['owner'].split(':')[1]),0)
job=next(j for j in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if j['id']=='2ee720363d7d')
validate(key=CURRENT_KEY)
result=run_worker(row,'resume_safe');print(result)
obs=observation(job);assert obs and obs['verified'] and obs['target']==row['source_key'];(B/'recovery-delivery-observation.json').write_text(json.dumps(obs,ensure_ascii=False,indent=2))
print(json.dumps(obs))
