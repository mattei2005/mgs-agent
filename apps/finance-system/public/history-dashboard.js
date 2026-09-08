/* Closed months use the normal Dashboard shell; frozen values, no engine or writes. */
(function(G){
'use strict';
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim();
const val=c=>c?.kind==='numberValue'?c.value:null,col=n=>{let s='';while(n){const r=(n-1)%26;s=String.fromCharCode(65+r)+s;n=Math.floor((n-1)/26);}return s;};
/* Layout discovery from each frozen month. No formula evaluation or August coordinates. */
function closedBlocks(doc){
 const cs=doc.cells,at=new Map(cs.map(c=>[c.a1,c])),axis=doc.book==='principal'?2:1;
 const dates=cs.filter(c=>c.col===axis&&c.number_format?.type==='DATE'&&c.kind==='numberValue');
 const starts=dates.filter((c,i)=>i===0||dates[i-1].row!==c.row-1),out=[];
 for(const start of starts){
  const header=start.row-2,headers=cs.filter(c=>c.row===header&&c.col>axis&&c.kind==='stringValue'&&c.formatted.trim());
  let groups=[],g;
  for(const h of headers){if(!g||h.col>g.headers.at(-1).col+1){g={id:h.a1,headers:[]};groups.push(g);}g.headers.push(h);}
  const next=starts.find(x=>x.row>start.row),end=next?.row||doc.rows+1,total=cs.find(c=>c.col===axis&&c.row>=start.row&&c.row<end&&norm(c.formatted)==='total:');
  if(!total)continue;
  const days=dates.filter(c=>c.row>=start.row&&c.row<total.row);
  for(const b of groups){
   const gross=b.headers.find(c=>/gross/i.test(c.formatted)&&!/^ROI/i.test(c.formatted.trim()));if(!gross)continue;
   b.label=gross.formatted.split(/\n|Gross|GROSS/)[0].trim()||col(gross.col);
   b.tag=cs.find(c=>c.col===b.headers[0].col&&c.row===header-2&&/^G\d{3}$/.test(c.formatted.trim()))?.formatted||'';
   b.totalRow=total.row;b.firstRow=start.row;b.start=b.headers[0].col;b.end=b.headers.at(-1).col;
   b.monthly=b.headers.map(h=>at.get(col(h.col)+total.row)||null);
   b.days=days.map(day=>({date:new Date(Date.UTC(1899,11,30)+day.value*86400000).toISOString().slice(0,10),row:day.row,values:b.headers.map(h=>at.get(col(h.col)+day.row)||null)}));
   b.columns=b.headers.map(h=>h.formatted);
   const title=cs.find(c=>c.col===b.start&&c.row>total.row&&c.row<start.row+100&&/^Receita .*\$/i.test(c.formatted.trim())),stop=title&&cs.find(c=>c.col===b.start&&c.row>title.row&&c.row<title.row+25&&/^LUCRO:$/i.test(c.formatted.trim()));
   b.settlement=title&&stop?cs.filter(c=>c.col===b.start&&c.row>title.row&&c.row<=stop.row&&c.kind==='stringValue'&&c.formatted.trim()).map(c=>({label:c.formatted,reference:c.a1,values:cs.filter(x=>x.row===c.row&&x.col>b.start&&x.col<=b.start+4)})):[];
   out.push(b);
  }
 }
 return out;
}

function project(doc){
 if(doc.mode!=='closed-history'||doc.book!=='principal')throw Error('Fonte histórica incompatível com o Dashboard');
 const at=new Map(doc.cells.map(c=>[c.a1,c])),cashCell=r=>doc.caixa.find(c=>c.row===r&&c.col>2),cashValue=r=>val(cashCell(r)),sum=rs=>rs.every(r=>cashValue(r)!==null)?rs.reduce((s,r)=>s+cashValue(r),0):null;
 const required={2:'',58:'sub-total',75:'social media',77:'total',80:'usd',81:'reais'};
 for(const [row,label]of Object.entries(required)){if(cashValue(Number(row))===null)throw Error('Valor fechado do Caixa ausente: linha '+row);if(label&&!doc.caixa.some(c=>c.row===Number(row)&&c.col===2&&norm(c.formatted).includes(label)))throw Error('Indicador do Caixa mudou: '+row);}
 const fx=cashValue(2),cash={gross:cashValue(58),invalid:sum([59,60,61,62]),revshare:sum([67,68,69,70]),tax:cashValue(71),company_expenses:cashValue(72),personnel:cashValue(73),spend:cashValue(75),profit:cashValue(77),half_usd:cashValue(80),half_brl:cashValue(81),roi:cashValue(79)};
 const ranking=doc.caixa.filter(c=>c.col>2&&c.row>=5&&c.row<=56&&c.kind==='numberValue').map(c=>({label:doc.caixa.find(x=>x.row===c.row&&x.col===2)?.formatted||'',value:c.value,reference:c.a1})).filter(x=>x.label.trim()).sort((a,b)=>b.value-a.value);
 const staff=doc.cells.find(c=>c.col>=10&&c.col<=12&&c.row>100&&/^joe\s*-\s*gestor:/i.test(c.formatted.trim())),staffEnd=doc.cells.find(c=>c.row>100&&norm(c.formatted)==='salario e comissoes:');if(!staff||!staffEnd)throw Error('Bloco histórico de despesas não identificado');
 const labelsColumn=staff.col,first=doc.cells.find(c=>c.col===labelsColumn&&c.row>95&&c.row<staff.row&&/despesas (empresa|adicionais)/i.test(c.formatted));if(!first)throw Error('Bloco de despesas gerais ausente');
 const totalCompany=doc.cells.find(c=>c.col===labelsColumn&&c.row>first.row&&c.row<staff.row&&norm(c.formatted).includes('total de despesas adicionais'));
 function expense(c){const row=doc.cells.filter(x=>x.row===c.row&&x.col>c.col&&x.col<=labelsColumn+4),brl=row.find(x=>x.kind==='numberValue'&&/R\$/.test(x.formatted)),usd=row.find(x=>x.kind==='numberValue'&&/\$/.test(x.formatted)&&! /R\$/.test(x.formatted));const status=row.find(x=>x.col===(brl?.col||0)+1&&x.kind==='stringValue'&&/^(ok|conferido|a conferir)$/i.test(x.formatted.trim()));return {label:c.formatted.replace(/George/g,'Ícaro'),usd:val(usd),brl:val(brl),reference:c.a1,usd_ref:usd?.a1,brl_ref:brl?.a1,status:status?.formatted||'Não registrado',checked_on:null};}
 function expenseList(a,b,end){const rows=doc.cells.filter(c=>c.row>=a&&c.row<b&&c.col>=labelsColumn&&c.col<=labelsColumn+2&&c.kind==='stringValue'&&c.formatted.trim()&&!c.formatted.startsWith('[Conteúdo protegido')).map(expense).filter(x=>x.usd!==null||x.brl!==null);return {rows,total:end?expense(end):null};}
 const expenses={company:expenseList(first.row+1,totalCompany?.row||staff.row,totalCompany),personnel:expenseList(staff.row,staffEnd.row,staffEnd)};
 const calendarTotal=doc.cells.find(c=>c.col===2&&c.row>=30&&c.row<=37&&norm(c.formatted)==='total:');if(!calendarTotal)throw Error('Total mensal original não identificado');
 const countries=doc.cells.filter(c=>c.row===1&&/^RENDIMENTO TOTAL [A-Z]{2}$/.test(c.formatted.trim())).map(c=>({country:c.formatted.trim().split(' ').at(-1),reference:col(c.col)+calendarTotal.row,values:Array.from({length:7},(_,i)=>at.get(col(c.col+i)+calendarTotal.row)||null)}));
 const totalHeading=doc.cells.find(c=>c.row===1&&c.formatted.includes('RENDIMENTO MENSAL DE TODOS OS SITES JUNTOS'));
 const countryTotal=totalHeading?Array.from({length:7},(_,i)=>at.get(col(totalHeading.col+i)+calendarTotal.row)||null):null;
 // Domain groups derive from each month's own header and total row, never August offsets.
 const blocks=closedBlocks(doc),firstDataRow=blocks[0]?.firstRow;
 return {period:doc.period,read_only:true,fx,cash,ranking,expenses,countries,countryTotal,at,doc,daily:{blocks,firstDataRow,totalRow:calendarTotal.row},cashCell};
}
function render(doc,view,ui){
 const m=project(doc),{esc,fmt,dec,percent,panel,table,cards}=ui,number=(v,c='USD')=>v===null||v===undefined?'—':esc(fmt(v,c)),dual=c=>c?.kind==='numberValue'?number(c.value)+'<span class="subline">'+number(c.value*m.fx,'BRL')+'</span>':'—',show=c=>c?.kind==='errorValue'?'Indisponível':esc(c?.formatted||'');
 const sourceNote='<div class="summary-note">Mês fechado · valores preservados dentro da dash. Sem edição, atualização de câmbio ou aplicação das regras de agosto. Conversão visual em reais usa o câmbio fechado do Caixa.</div>';
 function expenses(category){const x=m.expenses[category],rows=x.rows.map(e=>[esc(e.label),number(e.usd===null?null:Math.abs(e.usd)),number(e.brl===null?null:Math.abs(e.brl),'BRL'),esc(e.status),'—']);if(x.total)rows.push(['TOTAL FECHADO NA ORIGEM',number(x.total.usd===null?null:Math.abs(x.total.usd)),number(x.total.brl===null?null:Math.abs(x.total.brl),'BRL'),'','']);const differs=x.total?.usd!==null&&Math.abs(x.total.usd-m.cash[category==='company'?'company_expenses':'personnel'])>.01;return '<div data-summary-expenses="'+category+'">'+panel(category==='company'?'Despesas Gerais':'Despesas dos funcionários',doc.sheet+' · somente leitura',table([category==='company'?'Despesa Tipo':'Gestor / funcionário','Valor $','Valor R$','Status original','Data da conferência'],rows,rows.map((_,i)=>i===rows.length-1?'subtotal':''))+sourceNote+(differs?'<div class="rule-note">O subtotal da principal difere do Caixa Sintético deste mês. Ambos foram preservados; os cartões usam o Caixa. Não foi criado ajuste para igualá-los.</div>':''))+'</div>';}
 const countryPanel=()=>panel('Resumo por país','Fechamento original por país · valores prontos, sem recomputar ROI.',m.countries.length?table(['País','Receita gross','Receita líquida','Impostos','Mídia','Lucro operacional','ROI gross','ROI net'],m.countries.map(c=>[esc(c.country),...c.values.slice(0,5).map(dual),...c.values.slice(5).map(show)]).concat(m.countryTotal?[['TOTAL OPERACIONAL',...m.countryTotal.slice(0,5).map(dual),...m.countryTotal.slice(5).map(show)]]:[]),m.countries.map(()=> '').concat(['subtotal'])):'<div class="panelbody">Esta origem não tem um fechamento separado por país. Os valores não foram inventados nem distribuídos retroativamente.</div>').replace('<section class="panel"','<section data-country-summary class="panel"');
 const strip='<section class="quote-strip" aria-label="Câmbio fechado"><div class="quote-strip-heading">Cotações e indicadores <small>Preservados no fechamento</small></div><div class="quote-strip-scroll"><div class="quote-item"><span>USD → BRL</span><strong>'+esc(dec(m.fx))+'</strong><small class="confirmed">Fechado</small></div><div class="quote-item"><span>ROI líquido do Caixa</span><strong>'+esc(m.cash.roi===null?'—':percent(m.cash.roi))+'</strong><small>Valor original</small></div></div></section>';
 function settlementTable(b){if(!b.settlement.length)return '';return '<h3>Fechamento do site</h3>'+table(['Componente','Valor $','Valor R$','Situação original'],b.settlement.map(r=>[esc(r.label),...r.values.filter(c=>c.number_format?.type!=='PERCENT').slice(0,3).map(show)]),b.settlement.map(r=>/LUCRO:/.test(r.label)?'subtotal':''));}
 function daily(){
 const picked=m.daily.blocks.find(b=>b.id===ui.selectedSite),blocks=m.daily.blocks.filter(b=>norm(b.label+' '+b.tag).includes(norm(ui.search)));
 const sourceValue=c=>c?.kind==='errorValue'?'Indisponível':c?.kind==='numberValue'?esc(c.formatted):'—';
 function metric(b,pattern){let indexes=b.headers.flatMap((h,i)=>pattern.test(h.formatted)?[i]:[]);const totals=indexes.filter(i=>/TOTAL/i.test(b.headers[i].formatted));if(totals.length)indexes=totals;return indexes.length?indexes.map(i=>sourceValue(b.monthly[i])).join('<span class="subline"></span>'):'—';}
 if(!picked)return panel('Domínios','Receitas e gastos do mês fechado. Abra o site para consultar todos os dias.','<div class="filters"><label>Buscar domínio<input id="siteSearch" value="'+esc(ui.search||'')+'" placeholder="Nome do site"></label></div>'+table(['Domínio','Receita gross','Receita líquida','Gastos','Lucro líquido','Consulta'],blocks.map(b=>[esc(b.label)+(b.tag?'<small> · '+esc(b.tag)+'</small>':''),metric(b,/^(?!ROI).*Gross|^(?!ROI).*GROSS/),metric(b,/^(?!ROI).*NET/),metric(b,/Gastos/i),metric(b,/LUCRO LIQUIDO/i),'<button data-site="'+b.id+'">Ver os dias →</button>']))+'<div class="tablefooter">'+blocks.length+' blocos de domínio · inclui países e blocos inferiores; cada valor permanece na moeda da origem.</div>');
 return '<button id="backSites" class="textbutton back">← Todos os sites</button>'+panel(picked.label+(picked.tag?' · '+picked.tag:''),'Relatório Diário · '+doc.sheet,blockTables(picked,esc,table,sourceValue)+settlementTable(picked)+sourceNote);
 }
 const c=m.cash,compositionRows=[['Receita gross',c.gross,''],['Inválidos',c.invalid,''],['Rev share',c.revshare,''],['Receita',c.revshare===null?null:c.gross+c.revshare,'subtotal'],['Impostos',c.tax,''],['Despesas Gerais',c.company_expenses,''],['Despesas dos funcionários',c.personnel,''],['Gastos com mídia',c.spend,''],['Resultado líquido total',c.profit,'subtotal'],['Líquido net · participação 50%',c.half_usd,'netrow'],['Estimativa do mês · 50%',c.half_usd,'estimate']];
 const composition=panel('Composição financeira','Receitas, deduções e resultado de '+doc.sheet,table(['Componente','Valor $','Valor R$'],compositionRows.map(([label,v])=>[esc(label),number(v),number(label.includes('50%')?c.half_brl:v===null?null:v*m.fx,'BRL')]),compositionRows.map(x=>x[2]))+sourceNote);
 const top=m.ranking.slice(0,6),max=Math.max(1,...top.map(x=>x.value)),ranking=panel('Sites em destaque','Maiores receitas fechadas no Caixa Sintético','<div class="panelbody barlist">'+top.map(x=>'<div class="baritem"><span>'+esc(x.label)+'</span><span>'+number(x.value)+'</span><div class="track"><span data-width="'+x.value/max*100+'"></span></div></div>').join('')+'</div><div class="tablefooter"><span>Receita bruta · USD</span><button class="textbutton" data-view="movement">Ver os dias →</button></div>');
 const warning=doc.previous_month_link&&!doc.previous_month_link.matches?'<div class="rule-note">Diferença preservada na origem: o mês anterior fecha em '+esc(doc.previous_month_link.previous_close.formatted)+' e este abre em '+esc(doc.previous_month_link.next_open.formatted)+'. Nenhum ajuste foi inventado.</div>':'';
 if(view==='company'||view==='personnel')return warning+expenses(view);
 if(view==='movement')return warning+daily();
 if(view==='rates'){const old=doc.period<'2026-03',params=[['Imposto',m.at.get('C1')],['Revshare',m.at.get('D1')],['USD → BRL',m.cashCell(2)],['USD → CAD',m.at.get(old?'G1':'H1')],['GBP → USD',m.at.get(old?'H1':'I1')]],invalid=m.daily.blocks.flatMap(b=>b.settlement.filter(r=>/invalido/i.test(norm(r.label))).map(r=>({b,r})));return strip+panel('Câmbio, imposto e revshare','Valores fixados no fechamento',table(['Parâmetro','Valor fechado','Situação'],params.map(([label,c])=>[label,show(c),'Fechado'])))+panel('Inválidos por domínio','Taxas e valores preservados; nenhuma reaplicação ao passado',table(['Domínio','Taxa fechada','Valor $','Valor R$','Situação original'],invalid.map(({b,r})=>[esc(b.label),show(r.values.find(c=>c.number_format?.type==='PERCENT')),show(r.values.find(c=>c.kind==='numberValue'&&!c.formatted.includes('R$')&&c.number_format?.type!=='PERCENT')),show(r.values.find(c=>c.kind==='numberValue'&&c.formatted.includes('R$'))),show(r.values.find(c=>c.kind==='stringValue'))])));}

 if(view==='sites')return daily();
 if(view==='accounts')return panel('Contas de anúncio',doc.sheet,'<div class="panelbody">O fechamento importado preserva os gastos financeiros, mas não inclui o cadastro de contas de anúncio desse mês. Não são exibidos vínculos de agosto como se fossem históricos.</div>');
 return warning+strip+cards([['Receita gross',c.gross,c.gross*m.fx,'Antes das deduções'],['Gastos com mídia',Math.abs(c.spend),Math.abs(c.spend)*m.fx,'Valor fechado'],['Líquido net · 50%',c.half_usd,c.half_brl,'Participação no resultado',true],['Estimativa do mês · 50%',c.half_usd,c.half_brl,'Período encerrado · sem extrapolação']])+ '<div class="grid-two"><div>'+composition+'</div><div>'+ranking+panel('Sua rotina em um lugar','Consulte o mês sem sair do Dashboard','<div class="panelbody"><button data-view="movement">Abrir relatório diário →</button><div class="rule-note">Dados fechados para consulta. Os valores não são recalculados.</div></div>')+'</div></div><div class="grid-two summary-expenses">'+expenses('company')+expenses('personnel')+'</div>'+countryPanel();
}
function blockTables(b,esc,table,show){
 const groups=[];let current;for(let i=0;i<b.headers.length;i++){const h=b.headers[i],p=h.formatted.trim().split(/\s+/),country=p.findLast(x=>/^(?:US|BR|GB|CA|MX|AR|DE|ES|ZA|TOTAL)$/.test(x))||'Geral';if(!current||current.country!==country||current.indexes.length>=10){current={country,indexes:[]};groups.push(current);}current.indexes.push(i);}
 return groups.map((g,index)=>'<details class="country-block manager-block" '+(index===0?'open':'')+'><summary>'+esc(g.country==='Geral'?'Detalhamento':g.country==='TOTAL'?'Total do site':g.country)+'</summary>'+table(['Dia',...g.indexes.map(i=>b.columns[i].replace(/\n/g,' · '))],b.days.map(d=>[esc(d.date.slice(8)+'/'+d.date.slice(5,7)),...g.indexes.map(i=>show(d.values[i]))]).concat([['TOTAL FECHADO',...g.indexes.map(i=>show(b.monthly[i]))]]),b.days.map(()=>'').concat(['subtotal']))+'</details>').join('');
}
G.HistoryDashboard={project,render,blocks:closedBlocks,blockTables};
})(globalThis);
