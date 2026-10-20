'use strict';
// Offline orchestration regression tests. API fixtures are NOT cloud receipts.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname,'../integrations/creative-archive-30tb/Pilot.js'),'utf8');
const config = JSON.parse(fs.readFileSync(path.join(__dirname,'../integrations/creative-archive-30tb/pilot-config.json'),'utf8'));
function harness(mode) {
 const state = {copies:0,landed:false,released:0,getIds:[],props:{MGS_ARCHIVE_PILOT_CONFIG:JSON.stringify(config)}};
 const source = {id:config.sourceFileId,name:'unit-pilot.mp4',mimeType:'video/mp4',parents:['1iGO8km_WVwbIppLotf1h1kZ7W0UKUxz1'],driveId:config.sourceDriveId,size:'5375929',md5Checksum:'59065739912275ee5995bfee8d5ca9c7',version:'12',trashed:false,capabilities:{canCopy:true}};
 const folder = {id:config.destinationFolderId,mimeType:'application/vnd.google-apps.folder',trashed:false,owners:[{emailAddress:config.account}],capabilities:{canAddChildren:true}};
 const copy = {id:'unitCopiedId',name:source.name,mimeType:source.mimeType,parents:[config.destinationFolderId],owners:[{emailAddress:config.account}],size:source.size,md5Checksum:source.md5Checksum,trashed:false};
 const context = {
  console:{log:()=>{}},
  LockService:{getScriptLock:()=>({tryLock:()=>mode!=='busy',releaseLock:()=>state.released++})},
  PropertiesService:{getScriptProperties:()=>({getProperty:k=>state.props[k]||null,setProperty:(k,v)=>{state.props[k]=v;}})},
  Drive:{About:{get:()=>({user:{emailAddress:mode==='wrongAccount'?'other@example.com':config.account}})},
   Permissions:{list:()=>({permissions:[{type:'user',emailAddress:'mgsagent@mgs-core-prod.iam.gserviceaccount.com',role:'writer'}]})},
   Files:{get:(id)=>{state.getIds.push(id);if(id===source.id)return {...source};if(id===folder.id)return {...folder};if(id===copy.id)return {...copy};throw new Error('unapproved parent lookup');},
    list:()=>({files:mode==='duplicates'?[{id:'one'},{id:'two'}]:(state.landed?[{id:copy.id}]:[])}),
    copy:()=>{state.copies++;if(mode==='lostBeforeLanding')throw new Error('NETWORK_AMBIGUOUS');state.landed=true;if(mode==='lostAfterLanding')throw new Error('NETWORK_AMBIGUOUS');if(mode==='mismatch')copy.md5Checksum='a'.repeat(32);return {id:copy.id};}
   }
  }
 };
 vm.createContext(context);vm.runInContext(code,context);
 return {state,run:()=>context.runArchivePilot()};
}
test('executes bounded copy path and leaves canonical SA readback pending',()=>{
 const h=harness();const r=h.run();assert.equal(r.status,'copy_verified_canonical_sa_readback_pending');assert.equal(r.sourceDeleted,false);assert.equal(h.state.copies,1);assert.equal(h.state.released,1);assert.ok(h.state.getIds.every(id=>[config.sourceFileId,config.destinationFolderId,'unitCopiedId'].includes(id)));
});
test('replay reuses landed copy instead of making another',()=>{const h=harness();const a=h.run();const b=h.run();assert.equal(a.destinationId,b.destinationId);assert.equal(h.state.copies,1);});
test('lost copy response reconciles landed exact copy on retry',()=>{const h=harness('lostAfterLanding');assert.throws(h.run,/NETWORK_AMBIGUOUS/);const r=h.run();assert.equal(r.destinationId,'unitCopiedId');assert.equal(h.state.copies,1);});
test('ambiguous failure with no visible copy blocks blind replay',()=>{const h=harness('lostBeforeLanding');assert.throws(h.run,/NETWORK_AMBIGUOUS/);assert.throws(h.run,/AMBIGUOUS_COPY_REQUIRES_RECONCILIATION/);assert.equal(h.state.copies,1);});
test('wrong account stops before any copy',()=>{const h=harness('wrongAccount');assert.throws(h.run,/EXECUTION_ACCOUNT/);assert.equal(h.state.copies,0);assert.equal(h.state.released,1);});
test('duplicate archive candidates stop before any copy',()=>{const h=harness('duplicates');assert.throws(h.run,/DUPLICATE_PILOT_COPIES/);assert.equal(h.state.copies,0);});
test('checksum mismatch yields no successful receipt',()=>{const h=harness('mismatch');assert.throws(h.run,/CHECKSUM/);assert.equal(h.state.props.MGS_ARCHIVE_PILOT_RECEIPT,undefined);assert.equal(h.state.released,1);});
test('busy pilot lock prevents all Google copies',()=>{const h=harness('busy');assert.throws(h.run,/PILOT_BUSY/);assert.equal(h.state.copies,0);});
