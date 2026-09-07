// Idempotent approved network migration; never resets review/payroll or monthly movements.
import {scenario,calculate} from './storage.mjs';import {siteCatalog} from './workspace.mjs';import {networkRules,seedNetwork,validateNetwork,networks} from './networks.mjs';import {isDeepStrictEqual} from 'node:util';
export function networkSeed(s){
 const additions=structuredClone(s.additions),overrides={...s.overrides};
 overrides[networkRules.rede2_key]??=networkRules.rede2_initial;
 for(const site of siteCatalog(s.result.domain,s.additions)){
  const i=additions.findIndex(a=>a.kind==='site'&&a.id===site.id),prior=i<0?{}:additions[i];
  if(prior.network_policy===networkRules.version)continue;
  const network=validateNetwork(seedNetwork(site));
  const row={...prior,kind:'site',id:site.id,name:site.name,new:site.new,status:site.status,network,partner:network,invalid_source:networks[network].invalid_source,network_policy:networkRules.version,network_authorization:networkRules.authorization};
  if(i<0)additions.push(row);else additions[i]=row;
 }
 if(!additions.some(a=>a.kind==='rate'&&a.key===networkRules.rede2_key))additions.push({kind:'rate',key:networkRules.rede2_key,value:overrides[networkRules.rede2_key],mode:'fixed',status:'provisional'});
 return {additions,overrides};
}
export async function migrateNetworks(db,{onProgress=()=>{},ids=null}={}){
 ids??=(await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows.map(r=>r.id);const out=[];
 for(const id of ids){
  const s=await scenario(db,id);if(s.state!=='draft')throw Error('Locked monthly workspace '+id);const seeded=networkSeed(s);
  if(isDeepStrictEqual(seeded.additions,s.additions)&&isDeepStrictEqual(seeded.overrides,s.overrides)){out.push({id,already_applied:true});continue;}
  const result=await calculate({...seeded,period:id.slice(10)});if(result.summary.counts.error||result.summary.domain.daily_failures)throw Error('Network calculation failed '+id);
  for(const k of ['gross','spend','company_expenses'])if(Math.abs(Number(result.domain.cash[k])-Number(s.result.domain.cash[k]))>1e-8)throw Error('Unrelated financial change '+id+' '+k);
  await db.transaction(async tx=>{
   const r=await tx.query("UPDATE scenarios SET additions=$1::jsonb,overrides=$2::jsonb,result=$3::jsonb,revision=revision+1,updated_at=now() WHERE id=$4 AND revision=$5 AND state='draft' RETURNING id",[JSON.stringify(seeded.additions),JSON.stringify(seeded.overrides),JSON.stringify(result),id,s.revision]);if(!r.rows.length)throw Error('Concurrent monthly edit; retry missing month '+id);
   await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)',[id,'Zeus / '+networkRules.authorization,'SITE_NETWORK_POLICY_APPLIED',JSON.stringify({additions:s.additions,overrides:s.overrides,cash:s.result.domain.cash}),JSON.stringify({authorization:networkRules.authorization,networks:result.domain.site_catalog.map(x=>({id:x.id,name:x.name,network:x.network})),cash:result.domain.cash})]);
  });
  const check=await scenario(db,id);if(!isDeepStrictEqual(check.additions,seeded.additions)||!isDeepStrictEqual(check.result.domain.cash,result.domain.cash))throw Error('Network readback mismatch');
  const item={id,readback:true,sites:check.result.domain.site_catalog.length,cash:check.result.domain.cash};out.push(item);onProgress(item);
 }
 return out;
}
