import {PERIODS,periodInfo,workspaceId,validDate} from './periods.mjs';
// Documentary catalog ONLY. This module has no import/write/rollover entrypoint.
// Existing calculation/import engines remain the sole executors of financial rules.
export const RULES=Object.freeze([
 {id:'sms-august',title:'SMS Funnel: valor aprovado de agosto',scope:'month',from:'2026-08',until:'2026-08',authority:'1551644766125428847',source:'reports/finance-august-adjust-1551644766125428847.md',description:'Exceção de agosto preservada. Não transformar o valor mensal em despesa recorrente.',after:'do_not_carry'},
 {id:'yolokfx-august',title:'Yolokfx integralmente MGS em agosto',scope:'month',from:'2026-08',until:'2026-08',authority:'1551644766125428847',source:'august_reconciliation.py / YOLO_POLICY_ID',description:'Exclusivo de agosto: SEM_COMISSAO/MGS. Nos outros meses, preservar a atribuição aprovada daquela competência.',policy:'august-yolokfx-mgs-1551644766125428847',after:'do_not_carry'},
 {id:'openzed-august',title:'Openzed: quatro origens devolvidas a Ícaro',scope:'month',from:'2026-08',until:'2026-08',authority:'1551714950781866035',source:'docs/finance-openzed-august-attribution.md',description:'Correção de quatro origens de agosto; não é regra geral de propriedade de Openzed.',after:'do_not_carry'},
 {id:'cpv16-august',title:'CPV16: mídia de Nicolas no fechamento de agosto',scope:'month',from:'2026-08',until:'2026-08',authority:'1551324490271695064',source:'august_reconciliation.py / POLICY_ID',description:'Ponte de reconciliação exclusiva de agosto, sem repetir gasto nos meses seguintes.',policy:'august-adops-cpv16-1551324490271695064',after:'do_not_carry'},
 {id:'wavesbee-cad',title:'WavesBee: ponte de moeda CAD autorizada',scope:'range',from:'2026-08',until:'2026-09',authority:'1546607083468623912',source:'currency_bridge.py / MONTHS',description:'Ponte autorizada para agosto e setembro. Continuidade em outubro exige confirmação; o cadastro de outubro não será corrigido automaticamente.',policy:'wavesbee-cad-1546607083468623912',after:'confirm'},
 {id:'payroll-monthly',title:'Remuneração mensal aprovada dos gestores',scope:'from',from:'2026-08',until:null,authority:'1546380179654451281',source:'references/trial-payroll-review.md',description:'Regra aprovada desde agosto: preservar pisos e faixas vigentes. O valor devido é calculado no próprio mês, nunca copiado do anterior.'},
 {id:'sbtech-cad',title:'SB Tech Bot: moeda CAD',scope:'from',from:'2026-07',until:null,authority:'1547697182948458611',source:'references/company-expense-source-order.md',description:'Moeda CAD desde julho. A existência do cadastro não comprova pagamento nem autoriza duplicar um lançamento.'},
 {id:'gross-originals',title:'Gross CAD e USD independentes',scope:'permanent',from:'2026-08',until:null,authority:'1551358728870035530',source:'reports/finance-publish-1551358728870035530.md',description:'Preservar os originais independentes; conversão não é receita adicional. Nenhum valor mensal deve ser copiado.'},
 {id:'boostingecon',title:'Boostingecon fora do rateio geral',scope:'from',from:'2026-09',until:null,authority:'1548317688051277918',source:'docs/finance-gam-email-automation.md',description:'Não participa do rateio desde setembro; receita residual não significa reativação automática.'}
].map(Object.freeze));
export function ruleState(rule,period){periodInfo(period);return period<rule.from?'future':rule.until&&period>rule.until?'expired':'active';}
const pick=(x,fields)=>Object.fromEntries(fields.filter(k=>x[k]!==undefined).map(k=>[k,x[k]]));
const SITE_FIELDS=['name','manager','managers','status','activity','archived','network','partner','input_currency','currency_policy','invalid_source'];
const EXPENSE_FIELDS=['label','category','mode','input','activity','archived','payroll_rule','manager_role'];
const authority=x=>/^\d{17,20}$/.test(String(x?.authorization||x?.authority||''))?String(x.authorization||x.authority):null;
function settings(s){
 const out=new Map(),additions=s.additions||[];
 for(const x of (s.result?.domain?.site_catalog||[])){if(x.id)out.set(x.id,{id:x.id,kind:'site',label:x.name||x.id,values:pick(x,SITE_FIELDS),authority:authority(x)});}
 for(const x of additions.filter(x=>x.kind==='site'))out.set(x.id,{id:x.id,kind:'site',label:x.name||out.get(x.id)?.label||x.id,values:{...out.get(x.id)?.values,...pick(x,SITE_FIELDS)},authority:authority(x)});
 for(const x of s.result?.domain?.expenses||[]){const a=additions.find(a=>a.kind==='expense'&&(a.target||a.id)===x.id)||{};out.set(x.id,{id:x.id,kind:'expense',label:a.label||x.label||x.id,values:{...pick(x,EXPENSE_FIELDS),...pick(a,EXPENSE_FIELDS)},authority:authority(a)});}
 return out;
}
function compareSettings(source,target,accounts={}){
 const a=settings(source),b=settings(target);for(const x of accounts.before||[])a.set('account:'+x.id,x);for(const x of accounts.after||[])b.set('account:'+x.id,x);return [...new Set([...a.keys(),...b.keys()])].sort().map(id=>{
  const before=a.get(id),after=b.get(id),keys=[...new Set([...Object.keys(before?.values||{}),...Object.keys(after?.values||{})])].sort();
  const changes=keys.filter(k=>JSON.stringify(before?.values[k])!==JSON.stringify(after?.values[k]));
  const state=!before?'added':!after?'absent':changes.length?'changed':'unchanged';
  return {id,kind:(after||before).kind,label:(after||before).label,state,changes,before:before?.values||null,after:after?.values||null,authority:after?.authority||null,requires_review:state!=='unchanged',financial_copy:false};
 });
}
export function buildPeriodPreview(source,target,accounts={}){
 const period=source.id?.replace(/^workspace-/,''),p=periodInfo(period);if(source.id!==workspaceId(period))throw Error('Cenário inválido');
 const next=PERIODS[PERIODS.findIndex(x=>x.id===period)+1]||null;
 if(target&&(!next||target.id!==workspaceId(next.id)))throw Error('Competência seguinte incompatível');
 const rules=RULES.map(r=>({...r,current_state:ruleState(r,period),next_state:next?ruleState(r,next.id):null,action:next&&r.until&&period<=r.until&&next.id>r.until?(r.after||'do_not_carry'):'consult'}));
 const pending=rules.filter(r=>r.action==='confirm').map(r=>({id:r.id,title:r.title,reason:r.description,authority:r.authority}));
 if(!target)pending.push({id:'missing-target',title:'Próxima competência indisponível',reason:next?'Cadastro ainda não disponível para comparação. Não foi criado.':'Fim do horizonte cadastrado. Não foi criada uma competência adicional.'});
 const controls=[];
 if(target){
  const rows=target.additions||[],invalid=rows.filter(x=>x.date&&!(validDate(next.id,x.date)||(x.kind==='monthly_gross_adjustment'&&x.period===next.id&&x.date===next.id)));
  controls.push({id:'target-date-scope',label:'Datas dos registros da próxima competência',status:invalid.length?'fail':'pass',items:invalid.map(x=>x.id)});
  const policies=rows.filter(x=>x.kind==='reconciliation_policy'||x.currency_policy),invalidPolicies=[];
  const ids=new Set();for(const x of policies){const id=x.currency_policy||x.id,r=RULES.find(r=>r.policy===id);if(ids.has(id)||x.period&&x.period!==next.id||r&&ruleState(r,next.id)!=='active')invalidPolicies.push(id);ids.add(id);if(!r)pending.push({id,title:'Política sem vigência mapeada',reason:'Não é possível inferir permanência nem copiar automaticamente. Cadastro atual preservado.'});}
  controls.push({id:'target-policy-scope',label:'Vigência das políticas identificadas',status:invalidPolicies.length?'fail':'pass',items:[...new Set(invalidPolicies)]});
  const confirmed=rows.filter(x=>x.checked_on||x.kind==='expense'&&/conferid|aprovad/i.test(x.status||''));
  if(confirmed.length)pending.push({id:'target-reviews',title:'Marcações de conferência existentes no destino',reason:'Verificar se são próprias da competência. Nenhuma marcação foi copiada ou apagada.'});
 }
 const cadastros=target?compareSettings(source,target,accounts):[];
 const counts={rules:rules.length,cadastros:cadastros.length,unchanged:cadastros.filter(x=>x.state==='unchanged').length,changes:cadastros.filter(x=>x.state!=='unchanged').length,pending:pending.length,fail:controls.filter(x=>x.status==='fail').length};
 return {period:p,next_period:next?.id||null,next_label:next?.label||null,revision:source.revision,account_revision:accounts.revision??null,target:target?{id:target.id,revision:target.revision}:null,read_only:true,apply_allowed:false,financial_writes:0,coverage:'Catálogo documental das decisões mapeadas, não inventário exaustivo de todo o motor. Cadastros mostram os dois meses já existentes; não são proposta de substituição.',rules,pending,controls,cadastros,counts,excluded:['Receitas e mídia realizadas','Pagamentos, créditos e ajustes pontuais','Valores de remuneração já calculados','Taxas efetivas e confirmações de fechamento','Marcações de conferência','Exceções com vigência encerrada'],notes:['Nenhum mês é aberto, fechado, recalculado ou alterado por esta prévia.','Cadastro de despesa não é comprovante nem novo lançamento; recorrência não é presumida.','Saldos anteriores seguem o ledger existente: não duplicar pagamentos para transportar saldo.','Diferenças entre cadastros exigem análise da decisão de origem, não correção automática.']};
}
