// Planner is prepended by the canonical Python runner; no credentials in payload.
import fs from 'node:fs/promises';import {gzipSync,gunzipSync} from 'node:zlib';import {createHash,randomUUID} from 'node:crypto';
import {openPostgres,calculate,root} from './storage.mjs';import {accountDocument} from './accounts.mjs';
let input='';for await(const c of process.stdin)input+=c;const cfg=JSON.parse(input);assert.ok(['plan','apply','recalc'].includes(cfg.mode));assert.ok(['mgs_finance','mgs_finance_monthroll_1555579357651537931','mgs_finance_monthprune_1556898264878419969'].includes(cfg.database));const stage=cfg.database!=='mgs_finance';const db=await openPostgres({database:cfg.database,user:stage?'mgs_pg':'mgsfinance',...(stage?{options:'-c role=mgsfinance'}:{})});
try{
 if(cfg.to>='2026-11'&&cfg.mode!=='recalc'){
  const {provisionNextPeriod}=await import('./workspace.mjs');
  console.log(JSON.stringify(await provisionNextPeriod(db,{from:cfg.from,to:cfg.to,apply:cfg.mode==='apply'})));
 }else{
 const sourceId='workspace-'+cfg.from,targetId='workspace-'+cfg.to,receiptId='month-rollover-'+cfg.to;assert.equal(nextMonth(cfg.from),cfg.to);
 const rows=(await db.query('SELECT * FROM scenarios WHERE id=ANY($1::text[])',[[sourceId,targetId,receiptId]])).rows,source=rows.find(x=>x.id===sourceId),target=rows.find(x=>x.id===targetId);assert.ok(source&&target,'monthly workspace missing');const receipt=rows.find(x=>x.id===receiptId),registry=await accountDocument(db);
 const audit=(await db.query("SELECT after_data FROM audit_events WHERE scenario_id=$1 AND action IN ('SITE_STATUS_CHANGED','SITE_NETWORK_REMOVED','SITE_NETWORK_ASSIGNED','SITE_REGISTERED')",[targetId])).rows;const protectedSites=[...new Set(audit.map(x=>x.after_data?.id).filter(Boolean))];
 let p=planRollover(source,target,registry,{protectedSites,previous:receipt?.result?.proof});
 if(cfg.mode==='recalc')p={...p,accounts:registry.accounts,additions:target.additions,changes:[],blocked:[],proof:null};
 if(p.blocked.length){console.log(JSON.stringify({pass:false,reason:'unresolved_monthly_mapping',blocked:p.blocked,from:cfg.from,to:cfg.to}));}
 else{
  const shouldCalc=!same(p.additions,target.additions)||cfg.mode==='recalc'||Number(target.result?.domain?.expenses?.find(x=>x.id==='company|121')?.usd||0)!==0;
  const calculated=shouldCalc?await calculate({period:cfg.to,overrides:target.overrides,additions:p.additions}):target.result;assert.equal(calculated.summary.counts.error||0,0);const oldReceipt=receipt?.result;
  const document={summary:{kind:'month_rollover',from:cfg.from,to:cfg.to,authority:AUTH},proof:p.proof};const receiptChanged=cfg.mode!=='recalc'&&!same(document,oldReceipt),workspaceChanged=!same(calculated,target.result)||!same(p.additions,target.additions),registryChanged=!same(p.accounts,registry.accounts);
  assert.deepEqual(p.additions.filter(x=>x.kind!=='site'),target.additions.filter(x=>x.kind!=='site'));assert.deepEqual(p.accounts.map(a=>({...a,bindings:undefined,auto_spend_binding:undefined,manager_bindings:undefined})),registry.accounts.map(a=>({...a,bindings:undefined,auto_spend_binding:undefined,manager_bindings:undefined})));
  assert.equal(Number(calculated.domain.expenses.find(x=>x.id==='company|121')?.usd||0),0,'SMS prepaid is still charged');
  const sourceMetrics=target.result.domain.cash,newMetrics=calculated.domain.cash;for(const k of ['gross','spend','direct_expenses'])assert.ok(Math.abs(Number(sourceMetrics[k]||0)-Number(newMetrics[k]||0))<1e-7,k+' original facts changed');assert.equal(calculated.domain.realized.cutoff_date,target.result.domain.realized.cutoff_date);
  let backup=null,auditId=null;
  if(cfg.mode!=='plan'&&(receiptChanged||workspaceChanged||registryChanged)){
   const dir=root+'/private/month-rollover-backups';await fs.mkdir(dir,{recursive:true,mode:0o700});backup=dir+'/'+cfg.to+'-'+randomUUID()+'.json.gz';const raw=JSON.stringify({source,registry,target,receipt:receipt||null}),gz=gzipSync(raw);await fs.writeFile(backup,gz,{flag:'wx',mode:0o600});assert.equal(gunzipSync(await fs.readFile(backup)).toString(),raw);
   await db.transaction(async tx=>{
    const locked=(await tx.query('SELECT id,revision FROM scenarios WHERE id=ANY($1::text[]) ORDER BY id FOR UPDATE',[[sourceId,targetId,'master-ad-accounts',receiptId]])).rows;for(const [id,revision] of [[sourceId,source.revision],[targetId,target.revision],['master-ad-accounts',registry.revision]])assert.equal(locked.find(x=>x.id===id)?.revision,revision,'concurrent revision changed');assert.equal(locked.find(x=>x.id===receiptId)?.revision??0,receipt?.revision??0);
    if(registryChanged)await tx.query("UPDATE scenarios SET additions=$1::jsonb,revision=revision+1,updated_at=now() WHERE id='master-ad-accounts'",[JSON.stringify(p.accounts)]);
    if(workspaceChanged)await tx.query('UPDATE scenarios SET additions=$1::jsonb,result=$2::jsonb,revision=revision+1,updated_at=now() WHERE id=$3',[JSON.stringify(p.additions),JSON.stringify(calculated),targetId]);
    if(receiptChanged)await tx.query("INSERT INTO scenarios(id,import_id,name,state,result) SELECT $1,import_id,$2,'draft',$3::jsonb FROM scenarios WHERE id=$4 ON CONFLICT(id) DO UPDATE SET result=excluded.result,revision=scenarios.revision+1,updated_at=now()",[receiptId,'Continuidade mensal '+cfg.to,JSON.stringify(document),targetId]);
    const ev=await tx.query('INSERT INTO audit_events(scenario_id,actor,action,before_data,after_data) VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id',[targetId,'Zeus / Rodolfo'+AUTH,cfg.mode==='recalc'?'SMS_CONSUMPTION_BASIS_RECALCULATED':'MONTH_END_CONFIGURATION_CARRIED',JSON.stringify({source_revision:source.revision,target_revision:target.revision,registry_revision:registry.revision,backup}),JSON.stringify({authority:AUTH,from:cfg.from,to:cfg.to,changes:p.changes,preserved:p.preserved,sms_basis:'consumption_only',no_financial_movements_copied:true})]);auditId=ev.rows[0].id;
   });
   const after=(await db.query('SELECT additions,result FROM scenarios WHERE id=$1',[targetId])).rows[0];assert.deepEqual(after.additions,p.additions);assert.deepEqual(after.result,calculated);assert.deepEqual((await accountDocument(db)).accounts,p.accounts);
  }
  console.log(JSON.stringify({pass:true,mode:cfg.mode,from:cfg.from,to:cfg.to,changes:p.changes,preserved:p.preserved,blocked:[],workspace_changed:workspaceChanged,registry_changed:registryChanged,receipt_changed:receiptChanged,readback:cfg.mode!=='plan',production_financial_writes:cfg.mode==='plan'?0:undefined,backup,audit_id:auditId,sms_expense_usd:calculated.domain.expenses.find(x=>x.id==='company|121')?.usd,company_before:sourceMetrics.company_expenses,company_after:newMetrics.company_expenses,cutoff:calculated.domain.realized.cutoff_date}));
 }
 }
}finally{await db.close();}
