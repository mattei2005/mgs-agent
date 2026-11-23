#!/usr/bin/env python3
"""Independent closure, ordered after the validator has exited."""
import importlib.util,pathlib,json,sys,time,os
s=importlib.util.spec_from_file_location('mgs_reboot_common',pathlib.Path(__file__).with_name('vps-maint-1574252891898908684-common.py'));assert s and s.loader;c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def main():
 lock=open(c.B/'closure.lock','a');c.fcntl.flock(lock,c.fcntl.LOCK_EX|c.fcntl.LOCK_NB)
 if (c.B/'final-result.json').exists() and c.load(c.B/'final-result.json').get('delivery_complete'):return 0
 final={'at':c.now(),'delivery_complete':False,'runtime_overall':False,'status':'closure_started'};c.atomic(c.B/'closure-progress.json',final)
 try:
  d=c.unit(c.VALIDATOR);assert d['ActiveState']=='inactive' and d['MainPID']=='0' and d['UnitFileState']=='disabled','validator exit/disable not proven'
  assert (c.B/'validator-exit-receipt.json').exists(),'validator did not finish durable receipt'
  result=c.load(c.B/'postboot-result.json');final['runtime_overall']=result['overall'];final['validator_exit_verified']=True
  c.run(['systemctl','disable',c.CLOSURE]);final['retained_units']='validator disabled/inactive; closure disabled and finishing; definitions retained without deletion'
  if not result['overall']:
   failed=[k for k,v in result.get('checks',{}).items() if not v];raise RuntimeError('post-boot gate: '+(','.join(failed) or result.get('diagnosis','unknown validator failure')))
  assert not c.run(['systemctl','--failed','--no-legend','--no-pager']).stdout.strip(),'failed unit after validator exit'
  phase='hostinger_completed_validated_remaining_hosts_pending'
  c.inventory_phase(phase,c.B/'postboot-result.json',{'hostinger_completed':True,'reboot_executed':True,'reboot_scheduled':False,'postboot_unit_state':'validator_disabled_inactive_definition_retained','reboot_transport_receipt':str(c.B/'final-result.json'),'next_gate':'Prepare next remote-host phase with host-scoped backup and Critical confirmation; do not infer authorization across hosts.'})
  def baseline(data):
   rows=[r for a in data.values() if isinstance(a,list) for r in a if isinstance(r,dict) and r.get('id')=='vps-runtime-package-baseline'];assert len(rows)==1
   rows[0].update({'latest_reboot_20261123':{'authorization_message_id':c.AUTH,'kernel':result['kernel'],'boot_id':result['boot_id'],'status':'completed_validated','result':str(c.B/'postboot-result.json')},'hostinger_reboot_state':'completed_validated','updated_at':c.now()})
  c.mutate_inventory(c.ROOT/'data/infra-inventory.json',baseline)
  c.checkpoint(phase,'Hostinger completed: new boot/kernel151, package and gateway/Discord checks passed; external validator disabled/inactive and definitions retained, no deletions. Closure transports and final receipt in '+str(c.B/'final-result.json')+'. Remaining MatteiInc01/02/03,Hestia and dashboard phases remain open with their exact gates; no repeat reboot.')
  c.audit('hostinger_postboot_closure_runtime_and_retention_verified',validator_disabled_inactive=True,kernel=result['kernel'],boot_id=result['boot_id'],receipt=str(c.B/'postboot-result.json'))
  git=c.git_ready(time.time()+690);final['git']=git
  evidence='Novo boot/kernel151; pacotes exatos; APT/Snap sem candidatos; dpkg/holds/failed/journal limpos;3 gateways com conexão Discord fresca; Hermes launcher/HEAD preservados; validator disabled/inactive, definitions retained; Git='+git['head'][:12]+'. Recibo: '+str(c.B/'postboot-result.json')
  final['report_infra']=c.report_once('Reboot Hostinger autorizado1574551205768732753 concluído e validado;demais4hosts/dashboard continuam pendentes.',evidence)
  text='**Hostinger concluída e validada.**\n\n- Novo boot confirmado com o kernel **6.8.0-151**.\n- Zeus, Atena e Ares voltaram a conectar ao Discord; serviços essenciais saudáveis.\n- Pacotes conferidos, sem atualizações normais pendentes e sem marcador de reboot.\n- Hermes, configurações e backups preservados; nenhuma limpeza de arquivos.\n- Inventário, checkpoint e REPORT-INFRA conferidos.\n\n**Esta fase da Hostinger terminou.** Os outros quatro servidores e o Node do dashboard continuam nas fases próprias, sem alterações por este reboot.'
  final['thread_post']=c.post_once('completion',text);final.update({'status':'completed_validated','delivery_complete':True,'finished_at':c.now()})
 except BaseException as error:
  final.update({'status':'blocked','exception_type':type(error).__name__,'diagnosis':str(error)[:700],'finished_at':c.now()});c.atomic(c.B/'final-result.json',final)
  c.audit('hostinger_external_closure_blocked',diagnosis=final['diagnosis'],runtime_overall=final['runtime_overall'],receipt=str(c.B/'final-result.json'))
  try:
   c.inventory_phase('hostinger_reboot_closure_blocked',c.B/'final-result.json',{'reboot_scheduled':False,'reboot_transport_receipt':str(c.B/'final-result.json')})
   c.checkpoint('hostinger_reboot_closure_blocked','Do not repeat reboot. Diagnose exact external result '+str(c.B/'final-result.json')+'; preserve successful runtime predicates and complete only failed closure/recovery layer. Other hosts unchanged.')
   final['blocker_report']=c.report_once('Validação/fechamento do reboot Hostinger bloqueado; não repetir reboot.',final['diagnosis']+'; runtime_overall='+str(final['runtime_overall'])+';receipt='+str(c.B/'final-result.json'))
   text='**A manutenção da Hostinger ainda não está encerrada.** O procedimento externo registrou um bloqueio de validação/fechamento: '+final['diagnosis']+'.\n\nO recibo foi preservado; nenhum segundo reboot foi disparado e os outros servidores não foram alterados. A recomendação é corrigir somente a camada pendente, sem repetir a reinicialização. É necessário revisar esse bloqueio antes de avançar para outro host.'
   final['thread_post']=c.post_once('blocker',text)
  except BaseException as secondary:final['delivery_blocker']=type(secondary).__name__+': '+str(secondary)[:250]
 finally:
  c.atomic(c.B/'final-result.json',final)
  # Seal retained evidence only after all delivery receipts have been written.
  files=[p for p in c.B.iterdir() if p.is_file() and not p.is_symlink() and p.name not in ['final-evidence.sha256','final-evidence-seal.sha256'] and not p.name.endswith('.lock')]
  r=c.run(['sha256sum']+sorted(str(p) for p in files));(c.B/'final-evidence.sha256').write_text(r.stdout);c.run(['sha256sum','-c',c.B/'final-evidence.sha256']);r=c.run(['sha256sum',c.B/'final-evidence.sha256']);(c.B/'final-evidence-seal.sha256').write_text(r.stdout);c.run(['sha256sum','-c',c.B/'final-evidence-seal.sha256'])
 return 0
if __name__=='__main__':sys.exit(main())
