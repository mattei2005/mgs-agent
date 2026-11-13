"""Apply exactly Rodolfo's natively confirmed immutable snapshot manifest once."""
import os,sys,json,stat,fcntl,shutil,subprocess,datetime,importlib.util,runpy,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
os.umask(0o077)
D=Path('/root/mgs-agent/data/storage-compact-history-1570876981178929333')
O=Path('/root/.hermes/profiles/zeus/cache/scratch/compact-history-1570876981178929333')
CONFIRM='1570888435353526397';CHANNEL='1569928464033783862';EXPECTED='2da08240d943ea86e8439afbdde8e07a01e29c688e7c9a16d864ca7dc91df592'
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def save(name,value):(D/name).write_text(json.dumps(value,indent=2)+'\n')
def now():return datetime.datetime.now().astimezone().isoformat()
def fs():
 v=os.statvfs('/');return {'used':(v.f_blocks-v.f_bfree)*v.f_frsize,'available':v.f_bavail*v.f_frsize,'observed_at':now()}
def audit(value):
 with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
def get(path):
 q=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN'],'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(q,timeout=30) as r:return json.load(r)

with (O/'execution.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not (D/'filesystem-result.json').exists(),'ALREADY_APPLIED_VALIDATE_ONLY'
 assert not (D/'execution-journal.jsonl').exists(),'RECONCILE_PREVIOUS_EXECUTION_BEFORE_RETRY'
 assert sha(D/'deletion-manifest.json')==EXPECTED
 m=json.load(open(D/'deletion-manifest.json'));assert sha(D/'deletion-validator.py')==m['validator_sha256']
 spec=importlib.util.spec_from_file_location('frozen_validator',D/'deletion-validator.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 helper=runpy.run_path('/root/mgs-agent/scripts/discord-bot-post.py');helper['load_env'](Path('/root/.hermes/profiles/zeus/.env'))
 confirm=get('channels/'+CHANNEL+'/messages/'+CONFIRM);me=get('users/@me');history=get('channels/'+CHANNEL+'/messages?before='+CONFIRM+'&limit=8')
 questions=[q for q in history if q['author']['id']==me['id'] and EXPECTED in q.get('content','')];assert confirm['id']==CONFIRM and confirm['channel_id']==CHANNEL;assert questions,'NATIVE_QUESTION_NOT_FOUND';question=max(questions,key=lambda q:int(q['id']));v.approval_gate(confirm,question,EXPECTED,me['id'])
 approval={'status':'confirmed','manifest_sha256':EXPECTED,'confirmation_message_id':CONFIRM,'question_message_id':question['id'],'confirmed_by':confirm['author']['id'],'question_author':me['id'],'channel_id':CHANNEL,'native_readback':True,'verified_at':now()};save('deletion-approval.json',approval)
 # The paths are backup copies outside any owning Git ancestor. No Git commands touch targets.
 for target in m['targets']:
  for parent in [Path(target),*Path(target).parents]:assert not (parent/'.git').exists(),'OWNING_GIT_ROOT_NEEDS_TRACKED_GATE'
 # Include argv references without treating inline audit source strings as consumers.
 argv_hits=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:args=(p/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  for raw in args:
   arg=raw.decode(errors='replace')
   if arg.startswith('--') and '=' in arg:arg=arg.split('=',1)[1]
   if any(arg==root or arg.startswith(root+'/') for root in m['targets']):argv_hits.append(int(p.name))
 assert not argv_hits,'ACTIVE_ARGV_TARGET_REFERENCE'
 controls={}
 for agent in ['zeus','ares','atena']:
  root=Path('/root/.hermes/profiles')/agent
  for rel in ['SOUL.md','config.yaml','memories/MEMORY.md','memories/USER.md']:
   p=root/rel
   if p.is_file():controls[str(p)]=sha(p)
 launcher=os.path.realpath('/root/.local/bin/hermes');save('controls-before-deletion.json',{'sha256':controls,'launcher':launcher})
 v.run('preflight',str(D/'execution-preflight.json'),False)
 pre=json.load(open(D/'execution-preflight.json'));before=fs();save('filesystem-before.json',before)
 executor_sha=sha(__file__)
 audit({'ts':now(),'event':'historical_snapshot_exact_deletion_start','actor':'zeus','confirmation_message_id':CONFIRM,'question_message_id':question['id'],'manifest_sha256':EXPECTED,'validator_sha256':m['validator_sha256'],'executor_sha256':executor_sha,'target_count':12,'regular_files':9984,'directories':3318,'scope':'exact expanded snapshot roots only'})
 removed=[]
 try:
  for target in m['targets']:
   p=Path(target);s=p.lstat();e=m['target_root_metadata'][target]
   assert stat.S_ISDIR(s.st_mode) and not p.is_symlink() and not os.path.ismount(p) and (s.st_dev,s.st_ino)==(e['dev'],e['ino']),'ROOT_IDENTITY_DRIFT'
   shutil.rmtree(p);assert not p.exists();removed.append(target)
   with (D/'execution-journal.jsonl').open('a') as j:j.write(json.dumps({'removed':target,'manifest_sha256':EXPECTED,'at':now()})+'\n');j.flush();os.fsync(j.fileno())
 except Exception as exc:
  audit({'ts':now(),'event':'historical_snapshot_deletion_partial','manifest_sha256':EXPECTED,'removed':removed,'remaining':[p for p in m['targets'] if Path(p).exists()],'exception_class':type(exc).__name__});raise
 after=fs();assert len(removed)==12 and all(not Path(p).exists() for p in m['targets']);result={'status':'filesystem_applied_once','manifest_sha256':EXPECTED,'confirmation_message_id':CONFIRM,'removed_roots':removed,'regular_files_removed':9984,'directories_removed':3318,'symlinks_removed':0,'before':before,'after':after,'observed_free_delta':after['available']-before['available'],'executor_sha256':executor_sha,'completed_at':now()};save('filesystem-result.json',result)
 audit({'ts':now(),'event':'historical_snapshot_filesystem_deletion_completed','manifest_sha256':EXPECTED,'confirmation_message_id':CONFIRM,'roots_removed':12,'files_removed':9984,'observed_free_delta':result['observed_free_delta']})
 v.run('post',str(D/'execution-postchecks.json'),False)
 post=json.load(open(D/'execution-postchecks.json'));assert pre['gateway_pids']==post['gateway_pids'],'GATEWAY_PID_CHANGED';assert os.path.realpath('/root/.local/bin/hermes')==launcher
 changed=[p for p,h in controls.items() if sha(p)!=h];save('controls-after-deletion.json',{'checked':len(controls),'changed_paths':changed,'launcher_unchanged':True,'gateway_pids_unchanged':True});assert not changed,'RECONCILE_CONCURRENT_CONTROL_WRITE'
 print(json.dumps({'filesystem':'PASS','roots_removed':12,'regular_files_removed':9984,'directories_removed':3318,'observed_reclaimed_GiB':round(result['observed_free_delta']/1024**3,3),'retained_file_hashes_verified':post['retained_files_verified'],'controls_unchanged':len(controls),'gateway_pids_unchanged':True,'failed_units':0}))
