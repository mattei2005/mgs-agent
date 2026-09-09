import pathlib,sys,json,hashlib,shlex,fcntl
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/spend-placement-1547012165150711858';sys.path.insert(0,str(R));sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
from finance_spend_sources import missing_spend_account
load_env();T='/home/mgsfinance/releases/pg-auth-1545934831664242748';S='/var/tmp/mgs-finance-api-1547015219325444107';DB='mgs_finance_api_1547015219325444107';B='/home/zeus/mgs-finance-backups/1547015219325444107-api-first';state=json.loads(pathlib.Path('/root/mgs-agent/data/finance-media-spend-state.json').read_text());source=json.loads(pathlib.Path(state['last_collection_path']).read_text());prior=source['api_scan'];classified=[]
for a in prior:
 if a['platform']=='google' and a.get('status') in ('CANCELED','CLOSED'):
  x=missing_spend_account(a,source['since'],source['until'],None,None,None);assert x['spend_status']=='unavailable_status' and 'spend_amount' not in x;classified.append(x)
 else:classified.append(a)
source['api_scan']=classified;source['scan_errors']=sum(x['spend_status'] not in ('ok','unavailable_status') for x in classified);source['availability_classification']={'source':state['last_collection_path'],'rule':'CANCELED/CLOSED official statuses are unavailable, not successful zero queries','observed_error':'CUSTOMER_NOT_ENABLED'};assert source['scan_errors']==0
payload=json.dumps(source).encode();(D/'reclassified-collection.json').write_bytes(payload)
ssh('sudo -n -u mgs_pg tee '+S+'/media-spend.mjs >/dev/null',(R/'media-spend.mjs').read_bytes())
out=json.loads(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/api-spend-cli.mjs '+DB+' --stage-test',payload,timeout=420));assert out['pass'] and out['readback'] and out['stage_replay_no_duplicate'] and out['api_query_errors']==0;(D/'classification-stage.json').write_text(json.dumps(out))
expected=json.loads((D/'api-published.json').read_text())['files']['media-spend.mjs'];target_hash=hashlib.sha256((R/'media-spend.mjs').read_bytes()).hexdigest()
with (R/'private/quote-sync.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 code='import pathlib,hashlib,shutil,os; p=pathlib.Path('+repr(T+'/media-spend.mjs')+');assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(expected)+';b=pathlib.Path('+repr(B+'/media-spend-before-closed-classifier.mjs')+');assert not b.exists();shutil.copy2(p,b);q=p.with_suffix(".availability-pending");shutil.copy2('+repr(S+'/media-spend.mjs')+',q);st=p.stat();os.chown(q,st.st_uid,st.st_gid);q.chmod(st.st_mode&0o777);os.replace(q,p);assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(target_hash)+';print("classifier published and read back")'
 print(ssh('sudo -n python3 -c '+shlex.quote(code)).strip())
proof={'pass':True,'sha256':target_hash,'prior_sha256':expected,'backup':B+'/media-spend-before-closed-classifier.mjs','unavailable_accounts':sum(x['spend_status']=='unavailable_status' for x in classified),'query_errors':0,'source':str(D/'reclassified-collection.json'),'stage_replay_no_duplicate':True};(D/'classification-published.json').write_text(json.dumps(proof));print(json.dumps(proof))
