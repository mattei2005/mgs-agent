'use strict';
// Executes the real pinned bootstrap + real worker against offline boundary fixtures.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const dir=path.join(__dirname,'../integrations/creative-archive-30tb');
const source=fs.readFileSync(path.join(dir,'Worker.js'),'utf8');
const boot=fs.readFileSync(path.join(dir,'Bootstrap.gs'),'utf8');
const fixture=fs.readFileSync(path.join(__dirname,'test_creative_archive_worker_orchestration.cjs'),'utf8');
const fn=fixture.slice(fixture.indexOf('function makeHarness('),fixture.indexOf("\ntest('owner worker"));
const makeHarness=new Function('vm','crypto','source','account','sa',fn+'\nreturn makeHarness;')(vm,crypto,source,'mgsdigitalcorp@gmail.com','mgsagent@mgs-core-prod.iam.gserviceaccount.com');
const config=JSON.parse(boot.match(/var config = (.+);/)[1]);
const codeId=boot.match(/getFileById\('([^']+)'\)/)[1];
function setup(mode,ack) {
 const h=makeHarness(undefined,config);h.texts[codeId]=mode==='tampered'?source+'\n// changed':source;
 const triggers=[];h.state.triggerCreates=0;h.state.scopeCalls=[];
 h.context.ScriptApp={AuthMode:{FULL:'FULL'},requireScopes:(auth,scopes)=>{h.state.scopeCalls.push({auth,scopes:Array.from(scopes)});if(mode==='missingScopes')throw new Error('SCOPE_REQUIRED');},getScriptId:()=>mode==='wrongProject'?'otherProject':'1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF',getProjectTriggers:()=>triggers,newTrigger:name=>({timeBased:()=>({everyMinutes:n=>({create:()=>{h.state.triggerCreates++;triggers.push({getHandlerFunction:()=>name});return {id:'offline-trigger'};}})})})};
 if(ack){h.metas.ack={id:'ack',parents:[config.requestsFolderId],lastModifyingUser:{emailAddress:'mgsagent@mgs-core-prod.iam.gserviceaccount.com',permissionId:'07414359829876449782'},properties:{mgsArchiveKey:'ack:'+config.canaryJobId,mgsArchiveType:'ack'}};h.texts.ack=JSON.stringify({schema:'mgs.archive.ack.v1',jobId:config.canaryJobId,kind:'canary',status:'verified',deleteSource:false});}
 vm.runInContext(boot,h.context);return h;
}
test('pinned bootstrap executes actual worker only after matching SHA-256',()=>{const h=setup();const r=h.context.mgsArquivoTeste();assert.equal(r.status,'ok');assert.equal(r.copied.length,1);assert.equal(h.state.copies,0);assert.equal(h.state.triggerCreates,0);});
test('tampered remote worker is never executed',()=>{const h=setup('tampered');assert.throws(()=>h.context.mgsArquivoTeste(),/CODIGO_DIVERGENTE/);assert.equal(h.state.writes.length,0);assert.equal(h.state.triggerCreates,0);});
test('another Apps Script project cannot run this bootstrap',()=>{const h=setup('wrongProject');assert.throws(()=>h.context.mgsArquivoTeste(),/PROJETO_INCORRETO/);assert.equal(h.state.writes.length,0);});
test('scheduler requires canonical SA canary acknowledgement',()=>{const h=setup();assert.throws(()=>h.context.mgsArquivoAtivar(),/AGUARDANDO_CONFERENCIA/);assert.equal(h.state.triggerCreates,0);});
test('acknowledged activation is idempotent and keeps deletion disabled',()=>{const h=setup(undefined,true);h.context.mgsArquivoAtivar();h.context.mgsArquivoAtivar();assert.equal(h.state.triggerCreates,1);assert.equal(h.state.copies,0);assert.equal(config.deleteSource,false);});
test('manifest explicitly covers dynamic Drive writes and planned trigger management',()=>{const m=JSON.parse(fs.readFileSync(path.join(dir,'appsscript.json'),'utf8'));assert.deepEqual(m.oauthScopes.slice().sort(),['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/script.scriptapp'].sort());assert.ok(m.dependencies.enabledAdvancedServices.some(s=>s.userSymbol==='Drive' && s.serviceId==='drive' && s.version==='v3'));});
test('missing OAuth scopes stop before worker writes or copy attempts',()=>{const h=setup('missingScopes');assert.throws(()=>h.context.mgsArquivoTeste(),/SCOPE_REQUIRED/);assert.equal(h.state.writes.length,0);assert.equal(h.state.copies,0);assert.equal(h.state.triggerCreates,0);});
test('scope guard explicitly checks the manifest-required scopes',()=>{const h=setup();h.context.mgsArquivoTeste();assert.equal(h.state.scopeCalls.length,1);assert.equal(h.state.scopeCalls[0].auth,'FULL');assert.deepEqual(h.state.scopeCalls[0].scopes.slice().sort(),['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/script.scriptapp'].sort());});
