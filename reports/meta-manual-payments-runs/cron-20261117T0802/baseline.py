import sys,json,os,fcntl
from pathlib import Path
B=Path(__file__).parent;sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_finance_continuity import read_workbook
import mgs_google_workspace_auth as g
c=json.loads((B/'contract-before.json').read_text());g.load_env();sa=g.load_service_account()
assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
t=g.service_account_access_token();code,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,name,capabilities,trashed',t,quota_project='mgs-core-prod');assert code==200 and d['capabilities']['canEdit'] and not d['trashed']
assert not (B/'workbook-before.json').exists()
with open('/root/mgs-agent/data/meta-manual-payments/writer.lock','a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 book=read_workbook(c);(B/'workbook-before.json').write_text(json.dumps(book,ensure_ascii=False));(B/'drive-before.json').write_text(json.dumps(d));fcntl.flock(f,fcntl.LOCK_UN)
print(json.dumps({'status':'prewrite_baseline_saved','sheets':len(book['sheets']),'drive_canEdit':True,'sheets_http':200,'identity':'service_account'}))
