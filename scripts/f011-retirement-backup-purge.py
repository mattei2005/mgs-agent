#!/usr/bin/env python3
"""Confirmed F011 one-shot: fail closed on any new owner instruction or byte drift."""
import pathlib,json,os,datetime,subprocess,importlib.util,urllib.request,urllib.error,fcntl,time,argparse
B=pathlib.Path('/root/mgs-agent');D=B/'data/f011-apply-1556720208696316077';CONF='1556731764217618587';SHA='d60cdc70fea3a5a446570a42fada9f37fa5479a6ce50c186be45c40264cd39dd';PLAN_SHA='36d9934d73a94f7f8965a7741d3cdb985e351b2e328783227664ba78e813060e';CORE_SHA='37af4d804f39e4b671b29f93fda9fe1c2529d1108e76cf4ad7c4cdae8c12f0f9';OWNER='344196393512075265';CHANNEL='1551768281688580096'
def load(path,name):
 s=importlib.util.spec_from_file_location(name,str(path));assert s is not None and s.loader is not None,'module_loader_missing';m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def pinned(path,hash_):assert subprocess.check_output(['sha256sum',str(path)],text=True).split()[0]==hash_,'pinned_dependency_changed'

def main(apply=False):
 os.umask(0o077);lock=(D/'backup-purge.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 pinned(D/'manifest.json',SHA);pinned(D/'backup-purge-plan.json',PLAN_SHA);core=B/'scripts/f011-retirement-backup-purge-core.py';pinned(core,CORE_SHA)
 plan=json.loads((D/'backup-purge-plan.json').read_text());plan['plan_sha256']=PLAN_SHA;now=datetime.datetime.now(datetime.timezone.utc)
 def auth():
  a=json.loads((D/'final-confirmation.json').read_text());assert a['confirmation_message_id']==CONF and a['manifest_sha256']==SHA and a['owner_id']==OWNER and a['confirmed_conditional_dump_disposal'] and a['backup_purge_hold'] is False,'instruction_or_hold_block'
 auth();assert json.loads((D/'retirement-closure.json').read_text())['status']=='PASS','retirement_not_verified'
 if apply and now < datetime.datetime.fromisoformat(plan['not_before']):return {'status':'retention_deferred','retention_elapsed':False,'writes':False}
 post=load(B/'scripts/discord-bot-post.py','f011_post');post.load_env(pathlib.Path(os.environ.get('MGS_DISCORD_BOT_ENV',str(post.DEFAULT_ENV))));token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
 def api(path):
  for attempt in range(3):
   try:
    q=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-F011-Retention/1.0'});return json.load(urllib.request.urlopen(q,timeout=20))
   except urllib.error.HTTPError as e:
    if e.code not in [429,500,502,503,504] or attempt==2:raise AssertionError('discord_readback_http_'+str(e.code)) from None
    time.sleep(2*(attempt+1))
   except (TimeoutError,urllib.error.URLError):
    if attempt==2:raise AssertionError('discord_readback_unavailable') from None
    time.sleep(2*(attempt+1))
  raise AssertionError('discord_readback_unavailable')
 evidence={'pages':0,'subsequent_owner_messages':0}
 def guard():
  auth();original=api('channels/'+CHANNEL+'/messages/'+CONF);assert original['id']==CONF and original['author']['id']==OWNER and original['content'].strip().casefold()=='sim','confirmation_readback_changed'
  cursor=None
  for page in range(100):
   messages=api('channels/'+CHANNEL+'/messages?limit=100'+('&before='+cursor if cursor else ''));evidence['pages']+=1
   assert isinstance(messages,list),'thread_history_unavailable'
   if any(x['author']['id']==OWNER and int(x['id'])>int(CONF) for x in messages):evidence['subsequent_owner_messages']+=1;raise AssertionError('later_owner_instruction_requires_review')
   if not messages or min(int(x['id']) for x in messages)<=int(CONF) or len(messages)<100:return True
   cursor=str(min(int(x['id']) for x in messages))
  raise AssertionError('thread_history_not_fully_reconciled')
 guard()
 # No instruction text/credentials leave the process. Only metadata proves the gate.
 transport=load(pathlib.Path('/root/.hermes/profiles/zeus/workspace/carcreditad-complete-reaudit-20261001/audit_transport.py'),'f011_transport')
 payload=core.read_text()+"\nPLAN="+repr(plan)+"\nAPPLY="+repr(apply)+"\nNOW="+repr((now if apply else max(now,datetime.datetime.fromisoformat(plan['not_before']))).isoformat())+"\n"+'''
try:
 os.umask(0o077)
 lock=open('/var/lock/mgs-f011-retirement-backup-purge.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 print(json.dumps({'ok':True,'result':run(PLAN,datetime.datetime.fromisoformat(NOW),apply=APPLY,guard=lambda:True)}))
except AssertionError as e:print(json.dumps({'ok':False,'guard_failure':str(e)}))
except Exception as e:print(json.dumps({'ok':False,'guard_failure':'remote_'+type(e).__name__}))
'''
 # Repeat the complete live owner gate immediately before the single remote mutation.
 guard();out=transport.remote('02',payload,timeout=120)
 if out['rc']!=0:
  guard();out=transport.remote('02',payload,timeout=120)
 assert out['rc']==0,'ssh_transport_failed_after_safe_retry';parsed=json.loads(out['stdout']);assert parsed['ok'],parsed.get('guard_failure','remote_validation_failed')
 r=parsed['result'];assert r['status']==('completed' if apply else 'dry_run_validated'),'unexpected_remote_state'
 result={'status':r['status'],'retention_elapsed':now>=datetime.datetime.fromisoformat(plan['not_before']),'live_instruction_gate':evidence,'remote_receipt':r,'scope':'exact2dumps_only;otherbackups/receipts/rollbackpreserved'}
 if apply:
  # Independent exact remote readback of the persisted receipt and both absent paths.
  verify="import json,pathlib;P="+repr(plan)+";root=pathlib.Path(P['backup_root']);r=json.loads((root/'authorized-dump-purge-receipt.json').read_text());assert r['status']=='completed' and r['plan_sha256']==P['plan_sha256'];assert all(not pathlib.Path(x['path']).exists() and not pathlib.Path(x['path']).is_symlink() for x in P['files']);print(json.dumps({'status':'PASS','receipt':r}))"
  checked=transport.remote('02',verify,timeout=60);assert checked['rc']==0,'post_readback_transport_failed';got=json.loads(checked['stdout']);assert got['status']=='PASS' and got['receipt']==r,'post_readback_mismatch';result['independent_post_readback']=True
 path=D/('backup-purge-execution.json' if apply else 'backup-purge-live-dry-run.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,path)
 if apply:
  with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now.isoformat(),'event':'f011_authorized_two_dumps_purged','agent':'zeus','confirmation_message_id':CONF,'manifest_sha256':SHA,'plan_sha256':PLAN_SHA,'receipt_path':str(path),'removed_exact_paths':[x['path'] for x in plan['files']],'independent_post_readback':True})+'\n')
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');args=a.parse_args()
 try:
  r=main(args.apply)
  if args.apply and r['status']=='completed':print('F011: os dois backups de streamcb/mgpchat_5182 foram descartados após o prazo autorizado. Ausência e recibo validados; nenhum outro backup foi excluído.')
  elif r['status']=='retention_deferred':print('F011: retenção ainda vigente; nenhum backup excluído.')
  else:print(json.dumps({'status':r['status'],'retention_elapsed':r['retention_elapsed'],'live_gate':r['live_instruction_gate'],'validated_exact_dumps':len(r['remote_receipt']['validated']),'writes':False}))
 except Exception as e:
  reason=str(e) if isinstance(e,AssertionError) else ('credential_read_failed' if isinstance(e,subprocess.CalledProcessError) and e.cmd and e.cmd[0]=='op' else 'dependency_'+type(e).__name__)
  with (D/'backup-purge-blocked.json').open('w') as f:json.dump({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'blocked','reason':reason,'confirmation_message_id':CONF},f)
  print('<@344196393512075265> F011: descarte automático bloqueado. Diagnóstico: '+reason+'. Não repetirei exclusão fora do manifesto; os backups ainda presentes ficam preservados para sua decisão. Recomendação: revisar a instrução ou o gate indicado antes de liberar. Confirma a manutenção dos backups enquanto esse ponto é revisado?');raise SystemExit(1)
