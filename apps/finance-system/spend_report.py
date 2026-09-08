"""Human-facing financial notifications: API totals, site/day destination, actionable changes only."""
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json

def money(value,currency):
 text=format(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),',.2f').replace(',','_').replace('.',',').replace('_','.')
 return {'USD':'US$','BRL':'R$','CAD':'CA$','GBP':'£'}.get(currency,currency)+' '+text

def render_report(report):
 if not report.get('pass'):return {'title':'Gastos · preenchimento não confirmado','body':'Etapa: '+report.get('step','consulta')+'. Erro: '+report.get('error','não informado')+'. Não foram substituídos por zero os valores sem confirmação.','attention':True,'actionable':True,'signature':'error:'+report.get('step','')+':'+report.get('error','')}
 auto=report.get('auto_registration',{});new=auto.get('created',[]);bound=auto.get('bound',[]);exceptions=report.get('exceptions',[]);missing=[a for a in report.get('missing_accounts',[]) if a.get('spend_status')=='ok' and Decimal(a['spend_amount'])>0];errors=report.get('api_query_errors',0)
 start=report.get('since','');end=report.get('until','');lines=['Período: '+start+' a '+end+'.']
 for platform,p in report.get('api_totals',{}).items():lines.append(('Facebook' if platform=='meta' else 'Google Ads')+': '+str(p['accounts'])+' contas com gasto · '+' / '.join(money(v,c) for c,v in p['by_currency'].items())+' (API).')
 lines.append('Os gastos vinculados foram preenchidos nos Relatórios Diários dos sites.')
 if new:lines.append('\nContas cadastradas automaticamente:');lines.extend('• '+a['name'].replace('@','＠')+' → '+a['site'] for a in new[:16])
 if len(new)>16:lines.append('+ '+str(len(new)-16)+' cadastros registrados na auditoria.')
 if bound:lines.append('\nVínculos definidos:');lines.extend('• '+a['name'].replace('@','＠')+' → '+a['site'] for a in bound[:8])
 labels={'missing_mapping':'vínculo ainda não definido','ambiguous_mapping':'mais de um bloco possível no site','manual_conflict':'valor editado manualmente; preservado','currency_mismatch':'moeda divergente','source_error':'consulta não confirmada'}
 if exceptions:lines.append('\nPrecisa de decisão/conferência:');lines.extend('• '+a['name'].replace('@','＠')+': '+labels.get(a['reason'],'vínculo a conferir')+'.' for a in exceptions[:12])
 if missing:lines.append('\nCom gasto, mas sem site identificado com segurança:');lines.extend('• '+a['name'].replace('@','＠')+' · '+money(a['spend_amount'],a['currency']) for a in missing[:12])
 if errors:lines.append(str(errors)+' consultas não foram confirmadas; não foram tratadas como gasto zero.')
 lines.append('\nRelatório Diário: https://dash.mgsdigitalcorp.com/?view=movement&period='+report['period'])
 signature=hashlib.sha256(json.dumps({'exceptions':sorted((a['id'],a['reason']) for a in exceptions),'missing':sorted((a['platform'],a['account_id']) for a in missing),'errors':errors},sort_keys=True).encode()).hexdigest()
 body='\n'.join(lines);assert len(body)<=4096
 return {'title':'Gastos por site · '+end,'body':body,'attention':bool(exceptions or missing or errors),'actionable':bool(new or bound or exceptions or missing or errors),'new_accounts':bool(new or bound),'signature':signature}
