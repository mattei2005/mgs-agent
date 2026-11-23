#!/usr/bin/env python3
"""Detached, owner-confirmed reboot dispatcher. Never invoke in foreground."""
import importlib.util,pathlib,os,time,json,sys
s=importlib.util.spec_from_file_location('mgs_reboot_common',pathlib.Path(__file__).with_name('vps-maint-1574252891898908684-common.py'));assert s and s.loader;c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
s=importlib.util.spec_from_file_location('mgs_reboot_preflight',pathlib.Path(__file__).with_name('vps-maint-1574252891898908684-preflight.py'));assert s and s.loader;v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
def main():
 lock=open(c.B/'dispatch.lock','a');c.fcntl.flock(lock,c.fcntl.LOCK_EX|c.fcntl.LOCK_NB)
 if (c.B/'reboot-attempt.json').exists():raise RuntimeError('existing reboot attempt; never replay automatically')
 pre=c.load(c.B/'prestate.json');deadline=time.monotonic()+1200;handoff=None
 try:
  while True:
   msgs=c.discord_get(c.THREAD,'?after='+c.AUTH+'&limit=100')
   matches=[m for m in msgs if m.get('author',{}).get('id')=='1496296175014252634' and m.get('content','').strip()==c.HANDOFF]
   row=c.source_turn(c.routing('zeus'));same_session=row['entry'].get('session_id')==pre['source_session_id'];source_inactive=not row['entry'].get('active_turn_token');active=c.all_active_turns()
   if matches:
    handoff=max(matches,key=lambda m:int(m['id']))
    newer_human=[m for m in msgs if not m.get('author',{}).get('bot') and int(m['id'])>int(handoff['id'])]
    if newer_human:raise RuntimeError('new human input after handoff; hold reboot for source-thread reconciliation')
   observation={'at':c.now(),'handoff_id':handoff['id'] if handoff else None,'source_session_same':same_session,'source_turn_inactive':source_inactive,'active_turns':active};c.atomic(c.B/'dispatch-handshake-progress.json',observation)
   if handoff and same_session and source_inactive and not active:break
   if time.monotonic()>=deadline:raise RuntimeError('handoff/idle wait expired; host was not rebooted; see canonical routing observation')
   time.sleep(5)
  c.run(['apt-get','update','-qq'],timeout=180);v.check_preflight(installed=True,require_git=False)
  # Check canonical routing and the delivered exact handoff again immediately before dispatch.
  msg=c.discord_get(c.THREAD,'/'+handoff['id']);assert msg['content'].strip()==c.HANDOFF and msg['author']['id']=='1496296175014252634'
  assert not c.source_turn(c.routing('zeus'))['entry'].get('active_turn_token');assert not c.all_active_turns()
  assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==pre['boot_id']
  attempt={'at':c.now(),'state':'issuing_single_reboot','authorization_message_id':c.AUTH,'handoff_message_id':handoff['id'],'source_turn_inactive':True,'all_agent_turns_inactive':True,'boot_id_before':pre['boot_id'],'expected_kernel':pre['expected_kernel']};c.atomic(c.B/'reboot-attempt.json',attempt);c.audit('hostinger_reboot_dispatch_boundary',**attempt)
  # This primitive is confined to the detached systemd-owned executor.
  r=c.run(['systemctl','reboot'],timeout=60,check=False)
  attempt.update({'command_rc':r.returncode,'returned_at':c.now()});c.atomic(c.B/'reboot-attempt.json',attempt)
  if r.returncode:raise RuntimeError('systemd refused reboot rc='+str(r.returncode)+'; do not bypass inhibitors or replay')
  return 0
 except BaseException as error:
  result={'at':c.now(),'status':'dispatch_blocked','diagnosis':type(error).__name__+': '+str(error)[:600],'reboot_attempt_exists':(c.B/'reboot-attempt.json').exists()};c.atomic(c.B/'dispatch-blocked.json',result);c.audit('hostinger_reboot_dispatch_blocked',**result)
  try:
   # Native enablement is reversed, definitions retained; no file cleanup or gateway action.
   for unit in [c.VALIDATOR,c.CLOSURE]:c.run(['systemctl','disable',unit],check=False)
   c.inventory_phase('hostinger_reboot_dispatch_blocked',c.B/'dispatch-blocked.json',{'reboot_executed':False,'reboot_scheduled':False})
   c.checkpoint('hostinger_reboot_dispatch_blocked','Do not repeat reboot. Inspect '+str(c.B/'dispatch-blocked.json')+' and original handshake/attempt; recover only the exact failed gate. Existing owner confirmation remains scoped; other hosts unchanged.')
   c.report_once('Reboot Hostinger retido pelo gate externo; nenhuma repetição automática.',result['diagnosis']+';receipt='+str(c.B/'dispatch-blocked.json'))
   c.post_once('dispatch-blocker','**O reboot da Hostinger foi retido pelo procedimento de segurança.**\n\nDiagnóstico: '+result['diagnosis']+'.\n\nNão forcei a reinicialização nem alterei os outros servidores. Os recibos foram preservados; a próxima ação é reconciliar somente esse gate, sem repetir os pacotes já concluídos.')
  except BaseException as delivery:result['delivery_error']=type(delivery).__name__+': '+str(delivery)[:250];c.atomic(c.B/'dispatch-blocked.json',result)
  return 0
if __name__=='__main__':sys.exit(main())
