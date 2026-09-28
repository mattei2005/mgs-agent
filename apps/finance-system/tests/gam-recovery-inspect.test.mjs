import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {inspectImport} from '../gam-recovery-inspect.mjs';
import {prepareChange} from '../gam-revenue-core.mjs';
// Clearly synthetic fault-injection fixtures, never submitted to production.
function fixture(){
 const sha=createHash('sha256').update('synthetic-recovery-source').digest('hex'),date='2026-09-10',prefix='gam-email-'+date+'-'+sha.slice(0,12);
 const plan={schema_version:1,authorization_message_id:'1547983130038767755',mapping_authority_message_id:'1551587001629937686',processing_policy_authority_message_id:'1549047147465281658',mapping_rules_sha256:sha,date,period:'2026-09',scenario_id:'workspace-2026-09',source_bundle_sha256:sha,source_import_id:prefix,partial:false,blockers:[],mapped_totals:{USD:'10',CAD:'0'},blocked_totals:{USD:'0',CAD:'0'},source_totals:{USD:'10',CAD:'0'},entries:[{id:prefix+'|eggbev|US|g006-d|USD',source_import_type:'gam_email_daily',source_import_id:prefix,source_date:date,source_bundle_sha256:sha,source_manager_tag:'g006-d',source_vertical:'us-cc-en',site:'Eggbev',manager:'nicolas',country:'US',date,currency:'USD',gross:'10',spend:'0'}]};
 const row={id:plan.scenario_id,state:'draft',revision:1,overrides:{},additions:[{kind:'data_cutoff',date:'2026-09-09'}],result:{summary:{counts:{error:0}},results:Object.fromEntries([['F1','5'],['H1','1.4'],['I1','1.3'],['L1','0.01'],['D1','0.2'],['EW82','0.3'],['C1','0.05']].map(([k,actual])=>['principal|Agosto 2026|'+k,{actual}])),domain:{site_catalog:[{name:'Eggbev',network:'SB Rede1',invalid_source:'L1'}],facts:[],cash:{spend:-100,company_expenses:-50,personnel:-25},realized:{cutoff_date:'2026-09-09'}}}};
 return {row,plan,audits:[],recovery:[]};
}
function client(state){const calls=[];return {calls,query:async(q,args)=>{calls.push(q);assert.match(q,/^SELECT/);return {rows:q.includes('FROM audit_events')?state.audits:q.includes('SELECT id FROM scenarios')?state.recovery:args[0].startsWith('media-spend-')?[{result:{summary:{until:state.plan.date}}}]:[state.row]};}};}
function commit(s){const p=prepareChange(s.row,s.plan,{spendUntil:s.plan.date});s.row.additions=p.additions;s.row.result.domain.facts=p.entries.map(e=>({...e,gross:'10'}));s.row.result.domain.realized.cutoff_date=s.plan.date;s.row.revision++;}
test('inspect proves source absent only after scenario, audit and recovery reads',async()=>{const s=fixture(),tx=client(s),out=await inspectImport(tx,s.plan);assert.equal(out.disposition,'not_applied');assert.equal(out.pass,true);assert.equal(tx.calls.length,4);});
test('a real committed shape needs exact audit before recovery can claim success',async()=>{const s=fixture();commit(s);assert.equal((await inspectImport(client(s),s.plan)).pass,false);s.audits=[{id:9,action:'GAM_EMAIL_DAILY_IMPORTED',after_data:{source_bundle_sha256:s.plan.source_bundle_sha256}}];const out=await inspectImport(client(s),s.plan);assert.equal(out.disposition,'applied');assert.equal(out.verify.audit_id,9);assert.equal(out.verify.cutoff,s.plan.date);});
test('residual audit or recovery prevents claiming no prior side effects',async()=>{const s=fixture();s.recovery=[{id:'synthetic-recovery'}];assert.equal((await inspectImport(client(s),s.plan)).disposition,'partial');});
test('changed source blocks replay rather than overwriting it',async()=>{const s=fixture();commit(s);s.row.additions.find(a=>a.currency).gross='11';const out=await inspectImport(client(s),s.plan);assert.equal(out.pass,false);assert.equal(out.disposition,'conflict');});
