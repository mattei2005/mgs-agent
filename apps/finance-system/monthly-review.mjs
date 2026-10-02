import {createHash} from 'node:crypto';
import {periodInfo,validDate,today} from './periods.mjs';
import {ratesFor} from './workspace.mjs';
import {originalCurrency} from './gross-pairs.mjs';
const pick=(obj,keys)=>Object.fromEntries(keys.filter(k=>obj?.[k]!==undefined).map(k=>[k,obj[k]]));
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const SCALE=18n,TEN=10n**SCALE;
function scaled(value){
 if(value===null||value===undefined||value==='')throw Error('missing');
 const m=/^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(String(value));if(!m)throw Error('invalid');
 const power=Number(SCALE)+Number(m[4]||0)-(m[3]||'').length;if(Math.abs(power)>100)throw Error('out_of_range');
 const digits=BigInt(m[2]+(m[3]||'')),v=power>=0?digits*10n**BigInt(power):digits/10n**BigInt(-power);return m[1]==='-'?-v:v;
}
const display=v=>{const negative=v<0n;if(negative)v=-v;return (negative?'-':'')+String(v/TEN)+'.'+String(v%TEN).padStart(Number(SCALE),'0');};
export function decimalCompare(values,expected){
 try{const actual=values.reduce((s,v)=>s+scaled(v),0n),target=scaled(expected),delta=actual-target,bound=BigInt(values.length+1);return {status:(delta<0n?-delta:delta)<=bound?'pass':'fail',expected:String(expected),actual:display(actual),delta:display(delta),precision_only:delta!==0n&&(delta<0n?-delta:delta)<=bound};}
 catch{return {status:'pending',reason:'Valor ausente ou não numérico; não convertido em zero.'};}
}
const nativeMap=s=>new Map(s.additions.filter(a=>a.id&&a.site&&a.date&&!['site','account_spend'].includes(a.kind)).map(a=>[a.id,a]));
export function traceRows(s,{model={facts:{},inputs:{}},source=[]}={}){
 const entries=nativeMap(s),cells=new Map(source.map(c=>[c.id,c])),pairs=new Map(s.additions.filter(a=>a.kind==='gross_pair').map(a=>[a.target_type+'|'+a.target,a]));
 return s.result.domain.facts.filter(f=>Number(f.gross)||Number(f.spend)||entries.get(f.id)?.source_components?.some(c=>Number(c.gross))).map(f=>{
  const a=entries.get(f.id),originals={},inputKeys=[...new Set(model.facts[f.id]?.gross||[])],origins=[];
  const add=(currency,value)=>{if(value===null||value===undefined||value==='')return;try{scaled(value);originals[currency]=originals[currency]===undefined?String(value):display(scaled(originals[currency])+scaled(value));}catch{originals[currency]=null;}};
  if(a){const p=pairs.get('entry|'+a.id);if(p){add('CAD',p.cad);add('USD',p.usd);}else add(a.currency,a.kind==='direct_monthly_cost'?a.amount:a.gross);}
  else for(const key of inputKeys){const input=model.inputs[key],cell=cells.get(key);if(!input)continue;const p=pairs.get('input|'+key),value=s.overrides[key]??(s.id==='workspace-2026-08'?cell?.input:null);origins.push(key);if(p){add('CAD',p.cad);add('USD',p.usd);}else add(originalCurrency(input,f),value);}
  return {id:f.id,site:f.site,date:f.date,country:f.country,manager:f.manager,partner:f.partner,gross_usd:f.gross,spend_usd:f.spend,profit_usd:f.profit,originals,source_cells:origins,source_type:a?.source_import_type||(f.native_addition?'native_entry':'imported_sheet'),source_manager_tag:a?.source_manager_tag??null,source_bundle_sha256:a?.source_bundle_sha256??null,authority:a?.authority??a?.authorization??null,revenue_superseded:!!f.revenue_superseded,components:(a?.source_components||[]).map(c=>pick(c,['currency','gross','network','method','rows','assignment_authority','original_manager_tag','supersedes_assignment_authority'])),adjustments:(a?.assignment_adjustments||[]).map(c=>pick(c,['from','to','period','authority','source_row','delta_gross_usd'])),source_metadata_complete:!!a?.source_import_type||origins.length>0};
 });
}
export function buildMonthlyReview(s,{now=today(),managerChecks=[],audits=[],payments=[],model,source}={}){
 const period=periodInfo(s.id.slice(10)),d=s.result.domain,facts=d.facts,cash=d.cash,expenses=d.expenses.filter(e=>!e.archived),checks=[];
 const compare=(id,label,values,expected)=>checks.push({id,label,...decimalCompare(values,expected)});
 const emptySlots=facts.filter(f=>!f.native_addition&&['gross','invalid','net','tax'].every(k=>f[k]==='')),emptyIds=new Set(emptySlots.map(f=>f.id));
 for(const [key,label] of [['gross','Receita bruta informada: dias e ajustes mensais × total'],['invalid','Inválidos: componentes informados × total'],['net','Receita informada após inválidos e revshare'],['tax','Impostos informados'],['spend','Mídia: componentes × total']]){compare(key,label,facts.filter(f=>key==='spend'||!emptyIds.has(f.id)).map(f=>f[key]),cash[key]);if(emptySlots.length){checks.at(-1).empty_template_slots=emptySlots.length;checks.at(-1).coverage_note='Posições da planilha sem receita preenchida foram excluídas somente da soma de receitas, não tratadas como receita zero; seus gastos continuam na soma de mídia. Receita nativa é contada separadamente. Completude depende das fontes externas.';}}
 compare('company','Despesas gerais × composição financeira',expenses.filter(e=>e.category==='company').map(e=>e.usd),cash.company_expenses);
 compare('personnel','Remunerações individuais × folha',expenses.filter(e=>e.category==='personnel').map(e=>e.usd),cash.personnel);
 compare('net_result','Receita líquida − impostos − mídia − despesas − folha',[cash.net,cash.tax,cash.spend,cash.company_expenses,cash.personnel],cash.profit);
 compare('participation','Participação de 50% × resultado total',[cash.half_usd,cash.half_usd],cash.profit);
 checks.push({id:'calculation_errors',label:'Erros de cálculo',status:s.result.summary.counts.error?'fail':'pass',count:s.result.summary.counts.error||0});
 const monthlyIds=new Set(s.additions.filter(a=>['monthly_gross_adjustment','direct_monthly_cost'].includes(a.kind)&&a.period===period.id&&a.date===period.id).map(a=>a.id));
 const leaks=[...new Set([...facts.filter(f=>!validDate(period.id,f.date)&&!(f.monthly_closing&&f.date===period.id&&monthlyIds.has(f.id))).map(f=>f.id),...s.additions.filter(a=>a.period&&a.period!==period.id||a.date&&!validDate(period.id,a.date)&&!monthlyIds.has(a.id)&&!['expense','rate'].includes(a.kind)).map(a=>a.id||a.kind)])];
 checks.push({id:'period_isolation',label:'Datas e exceções pertencem somente a esta competência',status:leaks.length?'fail':'pass',items:leaks});
 const duplicateIds=facts.map(f=>f.id).filter((id,i,all)=>all.indexOf(id)!==i);checks.push({id:'unique_facts',label:'Identidade dos fatos sem duplicação',status:duplicateIds.length?'fail':'pass',items:[...new Set(duplicateIds)]});
 const future=period.id>now.slice(0,7),hasMovements=facts.some(f=>Number(f.gross)||Number(f.spend))||!!d.realized?.cutoff_date||payments.some(p=>p.entries?.some(e=>!e.voided_at&&e.period===period.id));
 if(future)checks.push({id:'future_movements',label:'Mês futuro sem movimentos ou corte herdados',status:hasMovements?'fail':'pass'});
 for(const m of managerChecks)checks.push({id:'manager_'+m.manager,label:'Gestor: '+m.manager,status:m.pass===true?'pass':m.pass===false?'fail':'pending',delta:m.delta??null});
 const rateRows=ratesFor(period.id).filter(r=>['fx','invalid'].includes(r.type)).map(r=>{const cfg=s.additions.find(a=>a.kind==='rate'&&a.key===r.key);return {key:r.key,label:r.label,type:r.type,value:cfg?.value??s.overrides[r.key]??s.result.results?.[r.key]?.actual??null,mode:cfg?.mode||(r.automatic?'auto':'fixed'),status:cfg?.status||'provisional'};});
 const traces=traceRows(s,{model,source}),rows=expenses.map(e=>pick(e,['id','label','category','usd','brl','mode','manager','activity','commission_rate','commission_base_brl','floor_brl','origin','source','checked_on','status']));
 const history=audits.map(a=>({id:a.id,actor:a.actor,action:a.action,created_at:a.created_at,authority:a.after_data?.authorization??a.after_data?.authority??null,source_bundle_sha256:a.after_data?.source_bundle_sha256??null}));
 const failures=checks.filter(c=>c.status==='fail').length,pending=checks.filter(c=>c.status==='pending').length;
 return {version:1,period,revision:s.revision,scenario_id:s.id,snapshot_hash:hash({revision:s.revision,overrides:s.overrides,additions:s.additions,cash,payments:payments.map(p=>({party:p.counterparty,previous:p.previous,due:p.due,balance:p.balance,entries:p.entries?.map(e=>pick(e,['id','version','amount_cents','direction','voided_at']))}))}),as_of:now,cutoff:d.realized?.cutoff_date??null,financial_writes:0,settled:false,external_validation:'not_reperformed',status:failures?'divergent':future?'planned':period.id===now.slice(0,7)?'in_progress':'provisional',counts:{pass:checks.filter(c=>c.status==='pass').length,fail:failures,pending,trace_rows:traces.length,expenses:rows.length},checks,cash,realized:d.realized??null,rates:rateRows,expenses:rows,payments:payments.map(p=>({counterparty:p.counterparty,label:p.party.label,previous:p.previous,due:p.due,balance:p.balance,provisional:p.provisional,entries:p.entries.filter(e=>e.period===period.id).map(e=>pick(e,['id','description','kind','amount_cents','direction','voided_at','effective_date','version']))})),history,policies:s.additions.filter(a=>a.kind==='reconciliation_policy').map(a=>pick(a,['id','period','site','manager','authorization'])),notes:['Esta conferência verifica consistência interna no mesmo snapshot. Não substitui demonstrativos das redes, extratos das contas de anúncio ou comprovantes de pagamento.','Conferido/A conferir nas despesas não prova conciliação externa. Ausência de fonte ou de valor não significa zero.','Centavos explicados são preservados. Os controles não aplicam tolerância geral de R$ 0,01; apenas a precisão decimal de 18 casas na recomposição interna.','A primeira entrega é de consulta: não fixa câmbio, bloqueia mês, registra pagamento nem modifica lançamentos.',...(period.id==='2026-08'?['Agosto foi conciliado na auditoria 1551718259718365296, com ressalvas imateriais de arredondamento. Câmbios automáticos continuam provisórios; esta consulta não reabre nem substitui aquela auditoria.']:[])]};
}
