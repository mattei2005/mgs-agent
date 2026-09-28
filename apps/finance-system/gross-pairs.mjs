import fs from 'node:fs/promises';
const sourceCells=new Map(JSON.parse(await fs.readFile(new URL('./private/source.json',import.meta.url),'utf8')).cells.filter(c=>c.id.startsWith('principal|Agosto 2026|')).map(c=>[c.id,{formula:c.formula}]));
const fail=message=>{throw Object.assign(Error(message),{status:400});};
const validateGross=value=>{const text=String(value);if(!/^-?\d+(\.\d{1,30})?$/.test(text)||!Number.isFinite(Number(text))||Math.abs(Number(text))>1e12)fail('Receita inválida');return text;};
export function originalCurrency(x,f){const root=f?.source?.gross&&sourceCells.get('principal|Agosto 2026|'+f.source.gross);if(x.metric==='gross'&&root&&(!root.formula||root.formula.startsWith('=SUM(')))return 'USD';return x.metric==='gross'&&x.book==='principal'&&x.source===f?.source?.gross?'USD':x.currency;}
export function pairValue(additions,type,target,currency,value){const old=additions.find(a=>a.kind==='gross_pair'&&a.target_type===type&&a.target===target);return old?{...old}:{target_type:type,target,cad:currency==='CAD'?String(value??''):'',usd:currency==='USD'?String(value??''):''};}
export function withGrossPairs(model,s){
 const byId=new Map(s.result.domain.facts.map(f=>[f.id,f])),byKey=new Map();for(const f of s.result.domain.facts)for(const k of model.facts[f.id]?.gross||[])if(!byKey.has(k))byKey.set(k,f);
 for(const [key,x] of Object.entries(model.inputs)){
  if(x.metric!=='gross')continue;
  const f=byId.get(x.fact_id)||byKey.get(key);const currency=originalCurrency(x,f);
  if(!['CAD','USD'].includes(currency)&&!(currency==='GBP'&&(Number(x.value||0)===0||s.additions.some(a=>a.kind==='gross_pair'&&a.target_type==='input'&&a.target===key))))continue;
  const type=x.kind?'entry':'input',target=x.kind?f?.id:key;if(!target)continue;x.gross_pair=pairValue(s.additions,type,target,currency,x.value);
 }
 return model;
}
export function putPair(additions,period,type,target,cad,usd){
 if(!['input','entry'].includes(type)||typeof target!=='string'||!target)fail('Origem da receita inválida');
 const clean=v=>v===''?'':validateGross(v);const row={kind:'gross_pair',id:'gross-pair:'+type+':'+target,period,target_type:type,target,cad:clean(cad),usd:clean(usd)};
 return {additions:[...additions.filter(a=>!(a.kind==='gross_pair'&&a.target_type===type&&a.target===target)),row],row};
}
export function applyPairs(additions,period,model,requests){
 if(!Array.isArray(requests)||requests.length>150)fail('Lote de receitas inválido');let next=additions;const seen=new Set(),changes=[];
 for(const p of requests){if(seen.has(p.key))fail('Receita repetida no formulário');seen.add(p.key);const x=model.inputs[p.key];if(x?.metric!=='gross'||!x.gross_pair)fail('Receita sem origem editável');const d=x.gross_pair;const result=putPair(next,period,d.target_type,d.target,p.cad,p.usd);next=result.additions;changes.push(result.row);}
 return {additions:next,changes};
}
