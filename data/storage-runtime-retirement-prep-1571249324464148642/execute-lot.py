"""Default is preflight. Destruction needs a new native owner-approval receipt."""
import pathlib,os,json,subprocess,shutil,argparse,datetime,importlib.util,sys
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');OWNER='344196393512075265'
def load_verifier():
 spec=importlib.util.spec_from_file_location('lot_verifier',OUT/'verify-lot.py');assert spec and spec.loader;mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def audit(event):
 event.update(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',thread_id='1569928464033783862')
 with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');a=parser.parse_args();v=load_verifier();manifest_path=OUT/'deletion-manifest.json';m=json.loads(manifest_path.read_text());digest=v.sha(manifest_path);assert digest==(OUT/'deletion-manifest.sha256').read_text().split()[0]
 if not a.execute:print(json.dumps(v.verify(m)));return
 approval=OUT/'approval.json'
 if not approval.is_file():raise RuntimeError('missing_native_owner_confirmation_no_deletion')
 p=json.loads(approval.read_text());assert p['owner_id']==OWNER and p['manifest_sha256']==digest and p['executor_sha256']==v.sha(__file__)
 assert p['confirmation_message_id'].isdigit()and p['confirmation_message_id']!=m['authority']['preparation_message_id'] and p['channel_id']=='1569928464033783862' and p['native_readback_verified']is True
 v.verify(m)
 marker=OUT/'execution-start.json';fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump({'manifest_sha256':digest,'confirmation_message_id':p['confirmation_message_id']},f);f.flush();os.fsync(f.fileno())
 audit({'action':'runtime_exact_lot_delete_start','manifest_sha256':digest,'confirmation_message_id':p['confirmation_message_id'],'paths':[r['path']for r in m['targets']]})
 removed=[]
 def journal(path):
  removed.append(path)
  with (OUT/'execution-journal.jsonl').open('a')as f:f.write(json.dumps({'path':path,'absent':not os.path.lexists(path),'at':datetime.datetime.now().astimezone().isoformat()})+'\n');f.flush();os.fsync(f.fileno())
 def same_root(path):
  row=next(r for r in m['targets']if r['path']==path);s=os.lstat(path);assert(s.st_dev,s.st_ino,s.st_mode)==tuple(row['root_identity'][k]for k in ['dev','ino','mode'])
 try:
  alias='/root/.local/bin/hermes-main-ad2d4822-mgs';same_root(alias);assert pathlib.Path(alias).is_symlink();os.unlink(alias);journal(alias)
  linked='/root/.hermes/hermes-agent-port-main-ad2d4822-mgs';same_root(linked);assert not pathlib.Path(linked).is_symlink()
  env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
  for k in ['GIT_DIR','GIT_COMMON_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY']:env.pop(k,None)
  subprocess.run(['git','-C','/root/.hermes/hermes-agent-port-main-59004a62-mgs','worktree','remove','--force',linked],check=True,capture_output=True,env=env);assert not os.path.lexists(linked);journal(linked)
  admin='/root/.hermes/hermes-agent-port-main-59004a62-mgs/.git/worktrees'
  if os.path.lexists(admin):same_root(admin);assert not any(pathlib.Path(admin).iterdir());os.rmdir(admin)
  journal(admin)
  standalone='/root/.hermes/hermes-agent-port-main-46904a3b-mgs';same_root(standalone);assert not pathlib.Path(standalone).is_symlink();shutil.rmtree(standalone);journal(standalone)
  check=v.verify(m,post=True);(OUT/'filesystem-result.json').write_text(json.dumps(check,indent=2)+'\n');audit({'action':'runtime_exact_lot_filesystem_completed','manifest_sha256':digest,'confirmation_message_id':p['confirmation_message_id'],'paths_absent':removed});print(json.dumps(check))
 except Exception as exc:
  audit({'action':'runtime_exact_lot_partial_failure','manifest_sha256':digest,'confirmation_message_id':p['confirmation_message_id'],'journaled_removed':removed,'absent_targets':[r['path']for r in m['targets']if not os.path.lexists(r['path'])],'error_type':type(exc).__name__});raise
if __name__=='__main__':
 try:main()
 except Exception as exc:print('BLOCKED: '+str(exc),file=sys.stderr);raise SystemExit(1)
