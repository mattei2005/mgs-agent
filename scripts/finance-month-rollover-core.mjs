import assert from 'node:assert/strict';
import {isDeepStrictEqual as same} from 'node:util';
export const AUTH='1555579357651537931';
export const SITE_FIELDS=['id','kind','new','name','domain','status','country','countries','manager','owner','managers','manager_names','native_account_managers','network','partner','currency','vertical','invalid_source','network_policy','network_authorization','network_additional_authorization','assignment_authority'];
const pick=x=>Object.fromEntries(SITE_FIELDS.filter(k=>Object.hasOwn(x,k)).map(k=>[k,structuredClone(x[k])]));
export function nextMonth(p){assert.match(p,/^\d{4}-\d{2}$/);const d=new Date(p+'-01T12:00:00Z');assert.equal(d.toISOString().slice(0,7),p);d.setUTCMonth(d.getUTCMonth()+1);return d.toISOString().slice(0,7);}
export function planRollover(source,target,registry,{protectedSites=[],previous=null}={}){
 const from=source.id.replace('workspace-',''),to=target.id.replace('workspace-','');assert.equal(nextMonth(from),to);assert.equal(target.state,'draft');assert.ok(to>='2026-10');
 const additions=structuredClone(target.additions),accounts=structuredClone(registry.accounts),changes=[],preserved=[],blocked=[],carriedSites=[],carriedAccounts=[];
 const oldSites=new Map((previous?.sites||[]).map(x=>[x.id,x]));const protectedSet=new Set(protectedSites);
 for(const src of source.additions.filter(x=>x.kind==='site')){
  const row=pick(src);assert.ok(row.id&&row.name);const index=additions.findIndex(x=>x.kind==='site'&&x.id===row.id),existing=index<0?null:additions[index],prior=oldSites.get(row.id);
  // Human/API target changes win. A differently authorized assignment is also explicit.
  if(existing&&(protectedSet.has(row.id)||['assignment_authority','network_authorization','network_additional_authorization'].some(k=>existing[k]&&src[k]&&existing[k]!==src[k]))){preserved.push({kind:'site',id:row.id});continue;}
  if(existing&&prior&&!same(pick(existing),prior)){preserved.push({kind:'site',id:row.id,reason:'target_changed_after_rollover'});continue;}
  const merged=existing?{...existing,...row}:row;
  // A setting removed from source may be intentionally target-specific; never erase by absence.
  if(!same(existing,merged)){if(index<0)additions.push(merged);else additions[index]=merged;changes.push({kind:'site',id:row.id,name:row.name});}
  carriedSites.push(pick(merged));
 }
 const names=new Set(additions.filter(x=>x.kind==='site').map(x=>x.name));
 const priorAccounts=new Map((previous?.accounts||[]).map(x=>[x.id,x]));
 for(const a of accounts){
  const old=priorAccounts.get(a.id),carried={id:a.id};let changed=false;const sourceSites=a.bindings?.[from]??a.source_sites??a.sites??[];
  for(const key of ['bindings','auto_spend_binding','manager_bindings']){
   if(!Object.hasOwn(a[key]||{},from))continue;
   const value=structuredClone(a[key][from]),current=a[key]?.[to];
   if(key==='bindings'&&value.some(x=>!names.has(x))){blocked.push({kind:'account',id:a.id,name:a.name,reason:'target_site_missing'});continue;}
   if(key==='auto_spend_binding'&&(!names.has(value.site)||!sourceSites.includes(value.site))){blocked.push({kind:'account',id:a.id,name:a.name,reason:'source_destination_conflict'});continue;}
   // Presence includes explicit empty binding: never resurrect a disabled target account.
   if(Object.hasOwn(a[key]||{},to)&&(!old||!Object.hasOwn(old,key)||!same(current,old[key]))){if(!same(current,value))preserved.push({kind:'account',id:a.id,key});continue;}
   if(key==='auto_spend_binding'&&Object.hasOwn(a.bindings||{},to)&&!a.bindings[to].includes(value.site)){preserved.push({kind:'account',id:a.id,key,reason:'explicit_target_site'});continue;}
   if(key==='manager_bindings'&&Object.hasOwn(a.bindings||{},to)&&!same(a.bindings[to],sourceSites)){preserved.push({kind:'account',id:a.id,key,reason:'explicit_target_site'});continue;}
   if(!same(current,value)){a[key]={...a[key],[to]:value};changed=true;}
   carried[key]=value;
  }
  if(changed)changes.push({kind:'account',id:a.id,name:a.name});
  if(Object.keys(carried).length>1)carriedAccounts.push(carried);
 }
 assert.ok(new Set(changes.filter(x=>x.kind==='site').map(x=>x.id)).size<=40,'Critical Subset: more than40site mutations');
 assert.deepEqual(additions.filter(x=>x.kind!=='site'),target.additions.filter(x=>x.kind!=='site'),'financial movements copied');
 const proof={sites:carriedSites,accounts:carriedAccounts};
 return {from,to,accounts,additions,changes,preserved,blocked,proof};
}
