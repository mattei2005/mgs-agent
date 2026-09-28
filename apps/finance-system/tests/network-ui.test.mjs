import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';
import {networks} from '../networks.mjs';import {rates,ratesFor,siteCatalog} from '../workspace.mjs';
test('M2 share exposes existing unique five-percent monthly engine binding',()=>{
 for(const period of ['2026-08','2026-09','2027-12']){const m=ratesFor(period).filter(r=>r.key==='principal|Agosto 2026|EW82');assert.equal(m.length,1);assert.equal(m[0].label,'RevShare M2');assert.equal(m[0].defaultValue,'0.05');assert.equal(m[0].type,'percent');assert.equal(m[0].automatic,false);assert.equal(networks.M2.share_source,'EW82');}
 assert.equal(rates.find(r=>r.key==='principal|Agosto 2026|D1').label,'Revshare Geral');
});import * as accounts from '../accounts.mjs';
test('exact approved rate labels and independent network parameter',()=>{for(const label of ['Imposto','Revshare Geral','USD → BRL','GBP → USD · YMonetize','Preço por Artigo','Inválidos SB Rede1','Inválidos SB Rede2'])assert.ok(rates.some(r=>r.label===label),label);assert.equal(new Set(rates.map(r=>r.key)).size,rates.length);assert.equal(rates.find(r=>r.label==='Inválidos SB Rede2').defaultValue,'0.004104');});
test('monthly site binding is part of site catalog model',()=>{const sites=siteCatalog({segments:[{id:'x',site:'TEST',status:'ATIVO',countries:['US'],manager:'joe',partner:'JBF'}]},[{kind:'site',id:'site-x',name:'TEST',new:false,status:'ATIVO',network:'SB Rede2'}]);assert.equal(sites[0].network,'SB Rede2');assert.equal(sites[0].partner,'SB Rede2');});
test('timezone validation accepts IANA and unknown blank, rejects typo',()=>{assert.equal(typeof accounts.validateTimezone,'function');assert.equal(accounts.validateTimezone('America/Sao_Paulo'),'America/Sao_Paulo');assert.equal(accounts.validateTimezone(''),null);assert.throws(()=>accounts.validateTimezone('Brazil/Fake'));});
test('rates and accounts UI hides Origem; checkbox and timezone editor',async()=>{const s=await fs.readFile(new URL('../public/app.js',import.meta.url),'utf8');const rates=s.slice(s.indexOf('function rateView'),s.indexOf('function accountEditor'));assert.ok(!rates.includes("'Origem'"));const editor=s.slice(s.indexOf('function accountEditor'),s.indexOf('function render'));assert.ok(editor.includes('type="checkbox"'));assert.ok(editor.includes('name="timezone"'));assert.ok(!editor.includes('multiple size='));});

test('unbound site keeps last valid financial rule and is explicit pending',()=>{
 const sites=siteCatalog({segments:[{id:'x',site:'TEST',status:'ATIVO',countries:['US'],manager:'joe',partner:'JBF'}]},[{kind:'site',id:'site-x',name:'TEST',new:false,status:'ATIVO',network:'SB Rede2',network_pending:true,network_binding_explicit:true}]);
 assert.equal(sites[0].network_pending,true);assert.equal(sites[0].network,'SB Rede2');assert.equal(sites[0].network_binding_explicit,true);
});
test('network ordering is alphabetical by domain family, principal first, without mutating sites',async()=>{
 const source=await fs.readFile(new URL('../public/app.js',import.meta.url),'utf8'),vm=await import('node:vm');
 const declarations=[source.split('\n').find(x=>x.startsWith('function siteDisplayName')),source.split('\n').find(x=>x.startsWith('const domains=')),source.slice(source.indexOf('function networkOrderedSites'),source.indexOf('function networkBindingsView'))].join('\n');
 const order=vm.runInNewContext(declarations+'\nnetworkOrderedSites;');
 const names=['FinanceTopFeed','Wantabrand Finance','Cliquet Finanzas','TopFeed Finanzas','Ducapes Finance','Wantabrand US-CC-ES + Wantabrand BR-CAR-BR','TopFeed','AutoCreditAdx','Cliquet','Ducapes'];
 const sites=Object.freeze(names.map((name,id)=>Object.freeze({name,id:String(id),network:'SB Rede1',status:'INATIVO'}))),before=JSON.stringify(sites);
 assert.deepEqual(Array.from(order(sites),s=>s.name),['AutoCreditAdx','Cliquet','Cliquet Finanzas','Ducapes','Ducapes Finance','TopFeed','FinanceTopFeed','TopFeed Finanzas','Wantabrand US-CC-ES + Wantabrand BR-CAR-BR','Wantabrand Finance']);assert.equal(JSON.stringify(sites),before);
 const subset=sites.filter(s=>s.name==='FinanceTopFeed'||s.name==='TopFeed Finanzas');assert.deepEqual(Array.from(order(subset,sites),s=>s.name),['FinanceTopFeed','TopFeed Finanzas']);
 const domainsOnly=[{id:'s',name:'Sub',domain:'finance.example.com.br'},{id:'o',name:'Other',domain:'other.com.br'},{id:'p',name:'Principal',domain:'example.com.br'},{id:'b',name:'Boundary',domain:'notexample.com.br'}];
 assert.deepEqual(Array.from(order(domainsOnly),s=>s.id),['p','s','b','o']);
 const css=await fs.readFile(new URL('../public/refinements.css',import.meta.url),'utf8');assert.ok(css.includes('grid-auto-flow: row'));
});
test('monthly network layout is compact and does not repeat allocation status',async()=>{
 const s=await fs.readFile(new URL('../public/app.js',import.meta.url),'utf8'),view=s.slice(s.indexOf('function networkBindingsView'),s.indexOf('function networkBindingEditor'));
 for(const token of ['network-grid','network-site-list','network-site-actions','network-site-count','network_pending','data-network-add','data-network-assign','data-network-remove'])assert.ok(view.includes(token),token);
 assert.ok(!view.includes('s.status'));assert.ok(!view.includes("'Status'"));assert.ok(!view.includes('table('));
 const css=await fs.readFile(new URL('../public/refinements.css',import.meta.url),'utf8');assert.ok(css.includes('.network-bindings .smallbutton'));assert.ok(css.includes('min-height: 43px'));assert.ok(css.includes('max-width: 700px'));
 const editor=s.slice(s.indexOf('function networkBindingEditor'),s.indexOf('function rateView'));assert.ok(editor.includes('status:selected.status'),'removing status presentation must preserve status in write payload');
});
test('rates UI has five monthly groups with assign transfer remove, no historic editing',async()=>{
 const s=await fs.readFile(new URL('../public/app.js',import.meta.url),'utf8');
 const groups=s.slice(s.indexOf('const invalidNetworkGroups='),s.indexOf('function networkBindingsView'));for(const key of Object.keys(networks))assert.ok(groups.includes("['"+key+"',"),key);
 for(const token of ['function networkBindingsView','function networkBindingEditor','data-network-assign','data-network-remove','binding_action','Último cálculo','network_pending'])assert.ok(s.includes(token),token);
});
