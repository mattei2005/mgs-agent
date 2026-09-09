import assert from 'node:assert/strict';import {isDeepStrictEqual} from 'node:util';import {accountManager,managerCodes} from './accounts.mjs';
export function assignManagers(registry,state,plan){
 assert.equal(plan.authority,'1547052028663169105');assert.equal(plan.period,'2026-09');assert.equal(state.id,'workspace-'+plan.period);assert.equal(plan.accounts.length,9);assert.equal(new Set(plan.accounts.map(x=>x.id)).size,9);
 const accounts=structuredClone(registry.accounts),additions=structuredClone(state.additions),changed=[];
 for(const p of plan.accounts){const a=accounts.find(x=>x.id===p.id);assert.ok(a?.verified);assert.equal(a.name,p.name);assert.equal(a.platform||'meta',p.platform);assert.ok(state.result.domain.facts.some(f=>f.site===p.site&&f.country===p.country&&f.segment===p.segment));
  const old=structuredClone(a);a.bindings={...a.bindings,[plan.period]:[p.site]};a.auto_spend_binding={...a.auto_spend_binding,[plan.period]:{site:p.site,country:p.country,segment:p.segment,authority:plan.authority,source:'explicit_Rodolfo_account_site_manager'}};
  if(p.code){assert.ok(managerCodes[p.code]);a.manager_bindings={...a.manager_bindings,[plan.period]:{code:p.code,...managerCodes[p.code]}};}
  if(!isDeepStrictEqual(a,old))changed.push({id:a.id,name:a.name,site:p.site,manager:accountManager(a,plan.period)});
 }
 for(const s of additions.filter(x=>x.kind==='site')){
  if(s.name==='Vizioid')Object.assign(s,{status:'ATIVO',manager:'MGS',owner:'MGS',assignment_authority:plan.authority});
  if(s.name==='Yolokfx')Object.assign(s,{manager:'COMPARTILHADO',manager_names:['MGS','Nicolas','Kelly','Joe','Ícaro','Isliago'],native_account_managers:true,assignment_authority:plan.authority});
  if(s.name==='Infinitynexx')Object.assign(s,{owner:'Joe',manager_names:['Joe','Ícaro'],assignment_authority:plan.authority});
 }
 for(const row of additions.filter(x=>x.kind==='account_spend')){const p=plan.accounts.find(x=>x.id===row.account_id);if(!p?.code)continue;const m=managerCodes[p.code];Object.assign(row,{manager_key:m.key,manager_code:p.code,manager_label:m.label});}
 return {accounts,additions,changed,workspace_changed:!isDeepStrictEqual(additions,state.additions)};
}
