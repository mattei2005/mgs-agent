'use strict';
/* Read-only annual projection, shared by the compact API and browser tests.
 * No financial rules, inputs or stored history are modified here. */
(function(G){
 const norm=x=>String(x||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
 const numeric=x=>x===null||x===undefined?null:Number.isFinite(Number(x))?Number(x):null;
 const sum=xs=>!xs.length||xs.some(x=>x===null||x===undefined)?null:xs.reduce((s,x)=>s+Number(x),0);
 const pair=(usd,brl)=>({usd:numeric(usd),brl:numeric(brl)}),plus=(a,b)=>pair(sum([a.usd,b.usd]),sum([a.brl,b.brl]));
 const aliases={contectageral:'ConectaGeral',conectageral:'ConectaGeral',financetopfeed:'Topfeed Finance',topfeedfinance:'Topfeed Finance',finanzastopfeed:'TopFeed Finanzas',newson:'Newsoun',newsonde:'Newsoun DE',newsonfinanzas:'Newsoun Finanzas',openzedus:'Openzed',openzedicarog001d:'Openzed',wantabranduscces:'Wantabrand',wantabrandbrcarbr:'Wantabrand',wantabranduscceswantabrandbrcarbr:'Wantabrand',dicasfinancas:'dicasfinancas.info',cephyricfr:'Cephyric',growpowerhubde:'Growpowerhub',helixenitde:'Helixenit',marevelxde:'Marevelx',xyvlovde:'Xyvlov',zyclorde:'Zyclor'};
 const siteName=x=>aliases[norm(x)]||String(x).trim();
 const expenseName=x=>String(x||'').trim().replace(/\s+/g,' ').replace(/:+$/,'').replace(/George/g,'Ícaro').replace(/^JBF (LeadsOn Hub|Tech Bot|Wire Fee)$/,'SB $1');
 function group(rows){const out=new Map();for(const x of rows){const label=expenseName(x.label),id=norm(label);if(out.has(id))out.get(id).value=plus(out.get(id).value,x.value);else out.set(id,{id,label,value:x.value});}return [...out.values()].sort((a,b)=>a.label.localeCompare(b.label,'pt-BR'));}
 function siteGroups(rows){const out=new Map();for(const x of rows){const label=siteName(x.label),id=norm(label);if(out.has(id)){const old=out.get(id);for(const k of ['gross','profit'])old[k]=plus(old[k],x[k]);}else out.set(id,{id,label,gross:x.gross,profit:x.profit});}return [...out.values()].sort((a,b)=>a.label.localeCompare(b.label,'pt-BR'));}
 function native(d){
  const r=d.domain.realized||d.domain.cash,c=d.domain.cash,days=d.period.days,elapsed=Number(r.elapsed_days??days),fx=Number(d.fx);
  if(!r||!c||!(fx>0)||!Number.isFinite(elapsed)||elapsed<0||elapsed>days)throw Error('Resumo mensal indisponível');
  const cv=v=>pair(v,numeric(v)===null?null:Number(v)*fx),cash={},ratio=elapsed/days;
  for(const k of ['gross','invalid','tax','spend','company_expenses','personnel','profit'])cash[k]=cv(r[k]);
  cash.revshare=cv(Number(r.net)-Number(r.gross)-Number(r.invalid));cash.sms=cv(r.direct_expense??r.direct_expenses??0);cash.other=cv(0);cash.half=pair(r.half_usd,r.half_brl);
  const cutoff=r.cutoff_date,fs=d.domain.facts.filter(f=>elapsed>0&&(!cutoff||f.date<=cutoff));
  const smsIds=new Set((d.additions||[]).filter(a=>a.kind==='direct_monthly_cost'&&/SMS/i.test(a.label)).map(a=>a.id)),embeddedSMS=fs.filter(f=>smsIds.has(f.id)).reduce((s,f)=>s+Number(f.spend||0),0);
  cash.sms=plus(cash.sms,cv(embeddedSMS));cash.spend=cv(Number(r.spend)-embeddedSMS);
  const sites=siteGroups([...new Set([...(d.sites||[]).map(s=>s.name),...fs.map(f=>f.site)])].map(label=>{const own=fs.filter(f=>f.site===label),general=d.domain.segments.filter(s=>s.site===label).reduce((s,x)=>s+Number(x.expenses||0),0)*ratio;return {label,gross:cv(own.reduce((s,f)=>s+Number(f.gross||0),0)),profit:cv(own.reduce((s,f)=>s+Number(f.profit||0),0)+general)};}));
  const rows=category=>group(d.domain.expenses.filter(e=>e.category===category&&!e.archived).map(e=>({label:e.label,value:cv(Number(e.usd)*ratio)})));
  const media={facebook:cv(0),google:cv(0)},seen=new Set(),accounts=new Map((d.accounts||[]).map(a=>[a.id,a]));
  for(const f of fs)for(const key of d.model?.facts?.[f.id]?.spend||[]){if(seen.has(key))continue;seen.add(key);const x=d.model.inputs[key];if(!x||x.value===''||x.value==null)continue;const a=accounts.get(x.account_id),label=x.source_label||x.label||'',platform=a?(a.platform||'meta'):/Google/i.test(label)?'google':/BM/i.test(label)?'meta':null;if(!platform)continue;let currency=platform==='google'&&/R\$/.test(label)?'BRL':x.currency,value=Number(x.value);if(!Number.isFinite(value))throw Error('Gasto não numérico');if(currency==='BRL')value/=fx;else if(currency!=='USD')continue;const k=platform==='google'?'google':'facebook';media[k]=plus(media[k],cv(-value));}
  cash.facebook=media.facebook;cash.google=media.google;cash.media_other=pair(cash.spend.usd-media.facebook.usd-media.google.usd,cash.spend.brl-media.facebook.brl-media.google.brl);
  const notes=[];if(elapsed<days)notes.push('Realizado até '+(cutoff||'nenhum dia completo')+'; despesas gerais e funcionários proporcionais aos dias completos.');
  if((d.rates||[]).some(r=>['fx','invalid'].includes(r.type)&&r.status!=='confirmed'))notes.push('Câmbio ou inválidos provisórios nesta competência.');
  return {period:d.period.id,state:elapsed===0?'empty':elapsed<days?'partial':'recorded',cutoff,fx,cash,sites,company:rows('company'),personnel:rows('personnel'),other:[],notes,revision:d.revision,financial_writes:0};
 }
 function historical(doc){
  const m=G.HistoryDashboard.project(doc),c=m.cash,cash={},monetary=row=>{const usd=row.values.find(c=>c.kind==='numberValue'&&/\$/.test(c.formatted)&&!/R\$/.test(c.formatted)&&c.number_format?.type!=='PERCENT'),brl=row.values.find(c=>c.kind==='numberValue'&&/R\$/.test(c.formatted));return pair(usd?.value??null,brl?.value??null);};
  for(const k of ['gross','invalid','revshare','tax','spend','company_expenses','personnel','profit'])cash[k]=pair(c[k],c[k+'_brl']);cash.half=pair(c.half_usd,c.half_brl);
  const sms=m.components.other.filter(x=>/sms.*consumo/i.test(x.label)),other=m.components.other.filter(x=>!/sms.*consumo/i.test(x.label));
  const aggregate=rows=>pair(rows.reduce((s,x)=>s+Number(x.usd||0),0),rows.every(x=>x.brl!==null)?rows.reduce((s,x)=>s+Number(x.brl),0):null);
  cash.sms=aggregate(sms);cash.other=aggregate(other);const seen=new Set(),sites=[];
  for(const b of m.daily.blocks){const rows=b.settlement.filter(r=>!seen.has(r.reference));for(const r of rows)seen.add(r.reference);const gross=rows.find(r=>/^receita\s*:/i.test(r.label.trim())),profit=rows.find(r=>/^lucro\s*:/i.test(r.label.trim()));if(!gross&&!profit)continue;
   // Settlement is the consolidated source: do not sum country/manager detail again.
   const heading=doc.cells.find(c=>c.col>=b.start&&c.col<=b.end&&c.row>b.totalRow&&c.row<b.firstRow+100&&/^Receita .*\$/i.test(c.formatted.trim()));
   const label=heading?heading.formatted.trim().replace(/^Receita\s+/i,'').replace(/\s*\$.*$/,'').trim():b.label;sites.push({label,gross:gross?monetary(gross):pair(null,null),profit:profit?monetary(profit):pair(null,null)});
  }
  const expenses=category=>group(m.expenses[category].rows.filter(e=>!(/SMS.*(?:recarga|pagamento).*n[aã]o ratear/i.test(e.label))).map(e=>({label:e.label,value:pair(e.usd,e.brl)})));
  // Prove each original platform total from its own labelled account column.
  let facebook=pair(0,0),google=pair(0,0);const headers=doc.cells.filter(c=>c.kind==='stringValue'&&(/Google Ads/i.test(c.formatted)||/^BM\s*-/.test(c.formatted))&&doc.cells.some(x=>x.col===c.col&&x.row===c.row+1&&/^preencher$/i.test(x.formatted.trim())));
  for(const h of headers){const totalRow=h.row+35,one=m.at.get(h.a1.replace(/\d+$/,String(totalRow))),next=doc.cells.find(c=>c.row===totalRow&&c.col===h.col+(/Google.*-R\$/i.test(h.formatted)?-1:1));if(one?.kind!=='numberValue')continue;const brl=/R\$/.test(one.formatted),converted=next?.kind==='numberValue'&&(/R\$/.test(next.formatted)!==brl);const value=pair(-Number(brl?(converted?next.value:one.value/m.fx):one.value),-Number(brl?one.value:converted?next.value:one.value*m.fx));if(/Google/i.test(h.formatted))google=plus(google,value);else facebook=plus(facebook,value);}
  cash.facebook=facebook;cash.google=google;cash.media_other=pair(c.spend-facebook.usd-google.usd,c.spend_brl===null?null:c.spend_brl-facebook.brl-google.brl);
  const notes=['Fechamento da própria aba mensal; USD e BRL originais preservados.'];
  const terms=['gross','invalid','revshare','tax','spend','company_expenses','personnel','sms','other'];
  const sourceDelta=cur=>{const value=sum(terms.map(k=>cash[k][cur]));return value===null?null:cash.profit[cur]-value;};cash.source_difference=pair(sourceDelta('usd'),sourceDelta('brl'));
  if(Math.abs(cash.source_difference.usd)>.005||Math.abs(cash.source_difference.brl)>.005)notes.push('O resultado original difere dos componentes da origem. Diferença exibida separadamente, sem ajuste financeiro.');
  return {period:doc.period,state:'closed',cutoff:doc.period+'-'+new Date(Number(doc.period.slice(0,4)),Number(doc.period.slice(5)),0).getDate(),fx:m.fx,cash,sites:siteGroups(sites),company:expenses('company'),personnel:expenses('personnel'),other:group(other.map(x=>({label:x.label,value:pair(x.usd,x.brl)}))),notes,source:doc.source_sha256,financial_writes:0};
 }
 G.AnnualCash={native,historical,siteName,expenseName,sum};
})(globalThis);
// Presentation only: October 2026 onward, using the engine's complete-day cutoff.
function compositionEstimates(data){
 const period=data.period?.id;if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(period||'')||period<'2026-10')return null;
 const r=data.domain.realized,p=data.domain.projection,c=data.domain.cash,days=Number(data.period.days),elapsed=Number(r?.elapsed_days),empty=()=>Array(12).fill(null);
 if(!r||!p||p.half_usd==null||!Number.isInteger(elapsed)||elapsed<=0||elapsed>days||!Number.isInteger(days)||days<28||days>31||p.state==='planned')return empty();
 const n=x=>Number(x||0),factor=days/elapsed,gross=n(r.gross)*factor,invalid=n(r.invalid)*factor,share=(n(r.net)-n(r.gross)-n(r.invalid))*factor;
 // Monthly fixed expenses are used once; partial later dates never enter this projection.
 return [gross,invalid,share,gross+share,n(r.tax)*factor,n(r.direct_expense)*factor,n(c.company_expenses),n(c.personnel),n(r.spend)*factor,n(p.half_usd)*2,n(p.half_usd),n(p.half_usd)];
}
function financialTotals(facts,general=0,staff=0){const v=x=>Number(x||0),r={};for(const k of ['gross','invalid','net','tax','spend'])r[k]=facts.reduce((s,f)=>s+v(f[k]),0);r.direct_expenses=facts.reduce((s,f)=>s+v(f.direct_expense),0);r.revshare=r.net-r.gross-r.invalid;r.general=v(general);r.staff=v(staff);r.profit=r.net+r.tax+r.general+r.staff+r.spend+r.direct_expenses;r.roi_gross=r.spend?r.gross/Math.abs(r.spend)-1:'';const cost=Math.abs(r.spend)+Math.abs(r.direct_expenses)+Math.abs(r.tax)+Math.abs(r.general)+Math.abs(r.staff);r.roi_net=r.spend&&cost?r.net/cost-1:'';return r;}
function grossOrigins(facts,data){const out={CAD:0,USD:0},seen=new Set();for(const f of facts){const keys=data.model?.facts[f.id]?.gross;if(keys?.length){for(const key of keys){if(seen.has(key))continue;seen.add(key);const x=data.model.inputs[key];if(!x)continue;const c=x.book==='principal'&&x.source===f.source?.gross?'USD':x.currency;out[c]=(out[c]||0)+Number(x.value||0);}}else{const a=(data.additions||[]).find(a=>a.id===f.id&&!a.kind);if(a)out[a.currency]=(out[a.currency]||0)+Number(a.gross||0);}}return out;}
function financialRows(data,site=null){const all=data.domain.facts.filter(f=>!site||f.site===site),general=site?data.domain.segments.filter(s=>s.site===site).reduce((s,x)=>s+Number(x.expenses||0),0):Number(data.domain.cash.company_expenses||0),staff=site?0:Number(data.domain.cash.personnel||0),days=data.period.days,elapsed=Math.max(0,Math.min(days,Number(data.domain.realized?.elapsed_days??days))),cutoff=data.domain.realized?.cutoff_date||null,stagedDates=new Set((data.additions||[]).filter(a=>a.source_import_type==='gam_email_daily'&&cutoff&&a.date>cutoff).map(a=>a.date)),rows=[];for(let day=1;day<=days;day++){const date=data.period.id+'-'+String(day).padStart(2,'0'),included=day<=elapsed,staged=!included&&stagedDates.has(date),items=included||staged?all.filter(f=>f.date===date):[];rows.push({date,included,staged,cutoff,origins:grossOrigins(items,data),...financialTotals(items,included||staged?general/days:0,included||staged?staff/days:0)});}const facts=all.filter(f=>!cutoff||f.date<=cutoff);rows.push({date:'TOTAL REALIZADO',total:true,cutoff,elapsed_days:elapsed,origins:grossOrigins(facts,data),...financialTotals(facts,general*elapsed/days,staff*elapsed/days)});return rows;}
