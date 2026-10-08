"""Daily success confirmations and actionable financial notifications."""
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json

def money(value,currency):
 text=format(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),',.2f').replace(',','_').replace('.',',').replace('_','.')
 return {'USD':'US$','BRL':'R$','CAD':'CA$','GBP':'£'}.get(currency,currency)+' '+text

def render_report(report):
 if not report.get('pass'):return {'title':'Gastos — preenchimento não confirmado','body':'**Problema:** a execução não foi concluída; ainda não posso confirmar o preenchimento.\n\n**Causa:** houve uma falha na consulta ou na conferência. O motivo exato ainda precisa ser confirmado.\n\n**Solução:** conferir a fonte e o que já foi gravado antes de retomar, sem duplicar valores. Essa verificação é minha; nenhuma decisão sua é necessária neste momento. Valores sem confirmação não foram tratados como zero.','attention':True,'actionable':True,'human_action_required':False,'signature':'plain-v3:'+report.get('until','')+':'+report.get('step','')+':'+report.get('error','')}
 auto=report.get('auto_registration',{});new=auto.get('created',[]);bound=auto.get('bound',[]);exceptions=report.get('exceptions',[]);missing=[a for a in report.get('missing_accounts',[]) if a.get('spend_status')=='ok' and Decimal(a['spend_amount'])>0];errors=report.get('api_query_errors',0)+report.get('source_errors',0)+len(report.get('discovery_errors',[]))
 start=report.get('since','');end=report.get('until','');attention=bool(exceptions or missing or errors)
 if attention:lines=['**Problema:** o preenchimento de '+start+' a '+end+' ficou parcial. Os gastos confirmados foram preenchidos; os pendentes não foram tratados como zero.']
 else:
  lines=['Período: '+start+' a '+end+'.']
  for platform,p in report.get('api_totals',{}).items():lines.append(('Facebook' if platform=='meta' else 'Google Ads')+': '+str(p['accounts'])+' contas com gasto · '+' / '.join(money(v,c) for c,v in p['by_currency'].items())+' (API).')
  lines.append('Os gastos vinculados foram preenchidos nos Relatórios Diários dos sites.')
 if new and not attention:lines.append('\nContas cadastradas automaticamente:');lines.extend('• '+a['name'].replace('@','＠')+' → '+a['site'] for a in new[:16])
 if len(new)>16 and not attention:lines.append('+ '+str(len(new)-16)+' cadastros registrados na auditoria.')
 if bound and not attention:lines.append('\nVínculos definidos:');lines.extend('• '+a['name'].replace('@','＠')+' → '+a['site'] for a in bound[:8])
 labels={'missing_mapping':'vínculo ainda não definido','ambiguous_mapping':'mais de um bloco possível no site','manual_conflict':'valor editado manualmente; preservado','currency_mismatch':'moeda divergente','source_error':'consulta não confirmada'}
 questions={'missing_mapping':'Em qual site e país esta conta deve entrar?', 'ambiguous_mapping':'Qual site e país devem receber os gastos desta conta?', 'site_not_unique':'Qual site deve receber os gastos desta conta?', 'country_not_unique':'Qual país do site deve receber os gastos desta conta?', 'manual_conflict':'Devo manter o valor manual ou usar o valor confirmado pela API?'}
 decisions=[a for a in exceptions if a.get('reason') in questions]
 technical=[a for a in exceptions if a.get('reason') not in questions]
 if technical or errors:
  lines.append('\n**Causa:** não consegui conferir estes dados na fonte; o motivo exato ainda precisa ser confirmado:')
  lines.extend('• '+a['name'].replace('@','＠')+': '+labels.get(a['reason'],'dados não confirmados')+'.' for a in technical)
  if errors:lines.append(str(errors)+' consultas não foram confirmadas; não foram tratadas como gasto zero.')
  lines.append('\n**Solução:** conferir a fonte e os valores já gravados antes de repetir. Essa investigação é minha; não cabe a você diagnosticar o sistema.')
 if decisions or missing:
  lines.append('\n**Causa:** há vínculo ambíguo ou conflito com um valor manual.\n\n**Solução:** preciso da sua definição nestes itens:')
  n=0
  for a in decisions:
   n+=1;lines.append(str(n)+'. '+a['name'].replace('@','＠')+': '+labels.get(a['reason'],'vínculo não definido com segurança')+'. '+questions[a['reason']])
  for a in missing:
   n+=1;lines.append(str(n)+'. '+a['name'].replace('@','＠')+' · '+money(a['spend_amount'],a['currency'])+' confirmado na API, sem vínculo seguro. Qual site e país devem receber esse gasto?')
 elif attention:lines.append('\nNenhuma decisão sua é necessária neste alerta.')
 if attention:lines.append('Estado: preenchimento parcial; isto não confirma o fechamento do dia.')
 unavailable=[a for a in report.get('api_unavailable',[]) if a.get('spend_status')=='unavailable_status']

 lines.append('\nRelatório Diário: https://dash.mgsdigitalcorp.com/?view=movement&period='+report['period'])
 signature=hashlib.sha256(json.dumps({'policy':'plain-v3','since':start,'until':end,'exceptions':sorted((a['id'],a['reason']) for a in exceptions),'missing':sorted((a['platform'],a['account_id']) for a in missing),'errors':errors},sort_keys=True).encode()).hexdigest()
 actionable=bool(new or bound or exceptions or missing or errors)
 if not actionable:
  # Rodolfo1547230494289174719: a short confirmation after each daily run.
  display_end='/'.join(reversed(end.split('-')))
  lines=['Facebook e Google Ads: gastos vinculados preenchidos nos Relatórios Diários até '+display_end+'.',
         'Período conferido: '+start+' a '+end+'.']
  if 'changed_sites' in report:lines.append(str(report['changed_sites'])+' sites atualizados nesta execução.' if report['changed_sites'] else 'Os valores já estavam atualizados; nenhuma alteração necessária.')

  lines.append('[Abrir Relatório Diário](https://dash.mgsdigitalcorp.com/?view=movement&period='+report['period']+')')
 body='\n'.join(lines)
 title='Gastos — preciso da sua definição · ' if decisions or missing else ('Gastos — preenchimento parcial · ' if attention else ('Gastos por site · ' if actionable else 'Gastos diários confirmados · '))
 return {'title':title+end,'body':body,'attention':attention,'actionable':actionable,'human_action_required':bool(decisions or missing),'new_accounts':bool(new or bound),'signature':signature}
