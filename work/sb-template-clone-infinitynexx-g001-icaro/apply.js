#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const { chromium } = require('/root/mgs-agent/tools/meta-library-collector/node_modules/playwright');

const SOURCE = 'Infinitynexx - MX-CC-ES/ES-ZW-SR - g004-d Joe';
const TARGET = 'Infinitynexx - MX-CC-ES/ES-ZW-SR - g001-d Icaro';
const OUT = '/root/mgs-agent/work/sb-template-clone-infinitynexx-g001-icaro';
const STATE = '/root/.local/share/mgs/smartbidding_state_headed.json';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36';
const STATUS_KEYS = new Set(['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']);

function secret(field) {
  return cp.execFileSync('op', ['item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field',field,'--reveal'], {encoding:'utf8'}).trim();
}
function csvCell(v) {
  const s = v == null ? '' : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
}
function cleanMessage(m) {
  const out = {};
  for (const [k,v] of Object.entries(m)) if (!STATUS_KEYS.has(k)) out[k] = v;
  return out;
}
function mutateLink(link) {
  if (!link) return link || '';
  const hits = [...link.matchAll(/([?&]utm_medium=)g004-d(?=(&|$))/g)];
  if (hits.length !== 1) throw new Error(`expected exactly one g004-d utm_medium in link, found ${hits.length}`);
  return link.replace(/([?&]utm_medium=)g004-d(?=(&|$))/g, '$1g001-d');
}
function desiredMessages(sourceMessages) {
  return sourceMessages.map(m => {
    const out = cleanMessage(m);
    for (const key of ['LINK_1','LINK_2']) if (out[key]) out[key] = mutateLink(out[key]);
    return out;
  });
}
function messagesCsv(messages) {
  const cols = [
    ['MESSAGE ID','MESSAGE_ID'],['TEXT','TEXT'],['DESCRIPTION','DESCRIPTION'],['IMAGE','IMAGE'],
    ['CTA 1','CTA_1'],['LINK 1','LINK_1'],['CTA 2','CTA_2'],['LINK 2','LINK_2'],['TEXT 2','TEXT_2']
  ];
  const lines = [cols.map(x=>x[0]).join(',')];
  for (const m of messages) lines.push(cols.map(([,key])=>csvCell(m[key] || '')).join(','));
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}
function parseMessages(row) {
  return typeof row.MESSAGES === 'string' ? JSON.parse(row.MESSAGES) : (row.MESSAGES || []);
}
function canonicalMessage(m) {
  const c = cleanMessage(m);
  const keys = ['MESSAGE_ID','TEXT','DESCRIPTION','IMAGE','CTA_1','LINK_1','CTA_2','LINK_2','TEXT_2'];
  const out = {}; for (const k of keys) out[k] = c[k] == null ? '' : c[k];
  return out;
}
function countMedium(messages, medium) {
  let count = 0;
  for (const m of messages) for (const k of ['LINK_1','LINK_2']) if ((m[k] || '').includes(`utm_medium=${medium}`)) count++;
  return count;
}
async function loginIfNeeded(page, context) {
  const body = await page.locator('body').innerText({timeout:15000});
  if (!body.includes('Log in to Smart Bidding') && !body.includes('Email address')) return;
  await page.locator('input[type="email"]:visible, input[name="username"]:visible, input[name="email"]:visible, input:visible').first().fill(secret('username'));
  await page.locator('input[type="password"]:visible').first().fill(secret('password'));
  await page.getByRole('button', {name:/Continue|Log in|Login/i}).first().click();
  await page.waitForLoadState('networkidle', {timeout:90000});
  await page.waitForTimeout(3000);
  await context.storageState({path:STATE});
}
async function selectDropdown(page, parent, currentLabel, option) {
  const combo = parent.getByRole('combobox', {name:currentLabel, exact:true});
  await combo.click();
  await page.waitForTimeout(300);
  const roleOption = page.getByRole('option', {name:option, exact:true});
  if (await roleOption.count()) await roleOption.last().click();
  else await page.getByText(option, {exact:true}).last().click();
  await page.waitForTimeout(500);
}
async function fetchRows(context, listUrl, headers) {
  const cleanHeaders = {...headers};
  for (const key of Object.keys(cleanHeaders)) if (key.startsWith(':') || ['host','content-length'].includes(key.toLowerCase())) delete cleanHeaders[key];
  const resp = await context.request.get(listUrl, {headers:cleanHeaders, timeout:120000});
  if (resp.status() !== 200) throw new Error(`readback GET failed HTTP ${resp.status()}`);
  const data = await resp.json();
  if (!Array.isArray(data)) throw new Error('readback response is not a list');
  return data;
}

(async () => {
  fs.mkdirSync(OUT, {recursive:true});
  const browser = await chromium.launch({headless:false, args:['--disable-blink-features=AutomationControlled']});
  const context = await browser.newContext({storageState:fs.existsSync(STATE)?STATE:undefined, viewport:{width:1600,height:1000}, userAgent:UA});
  const page = await context.newPage();
  let headers = null;
  let listUrl = null;
  const captured = [];
  const writeResponses = [];
  page.on('request', req => {
    if (req.url().includes('/broadcast/Messenger') && req.method() === 'GET') {
      headers = req.headers(); listUrl = req.url();
    }
  });
  page.on('response', async resp => {
    const method = resp.request().method();
    if (method !== 'GET' && resp.url().includes('api.jbfdigital.com.br')) {
      writeResponses.push({method, url:resp.url(), http:resp.status()});
    }
    if (resp.url().includes('/broadcast/Messenger') && resp.status() === 200 && method === 'GET') {
      try { const data = await resp.json(); if (Array.isArray(data)) captured.push(...data); } catch (_) {}
    }
  });
  try {
    await page.goto('https://app.smartbiddingdigital.com/accounts', {waitUntil:'networkidle', timeout:90000});
    await page.waitForTimeout(2500);
    await loginIfNeeded(page, context);
    try {
      await page.locator('.p-dropdown').first().click({timeout:10000});
      await page.waitForTimeout(500);
      await page.getByText('Messenger', {exact:true}).last().click({timeout:10000});
      await page.waitForTimeout(2500);
    } catch (_) {}
    await page.getByText('Broadcast Template', {exact:true}).click({timeout:15000});
    await page.waitForTimeout(7000);
    if (!headers || !listUrl) throw new Error('broadcast API headers/list URL not captured');
    const dedup = new Map(); for (const row of captured) dedup.set(row.ID || row.NAME, row);
    const rows = [...dedup.values()];
    const sources = rows.filter(r=>r.NAME===SOURCE);
    const targets = rows.filter(r=>r.NAME===TARGET);
    if (sources.length !== 1) throw new Error(`exact source count ${sources.length}`);
    if (targets.length !== 0) throw new Error(`target already exists count ${targets.length}`);
    const source = sources[0];
    const sourceMessages = parseMessages(source);
    if (sourceMessages.length !== 30) throw new Error(`source message count ${sourceMessages.length}, expected 30`);
    if (countMedium(sourceMessages,'g004-d') !== 30) throw new Error('source does not have exactly 30 g004-d links');
    const desired = desiredMessages(sourceMessages);
    if (countMedium(desired,'g004-d') !== 0 || countMedium(desired,'g001-d') !== 30) throw new Error('desired URL medium validation failed');
    const csvPath = path.join(OUT, 'target-import.csv');
    fs.writeFileSync(csvPath, messagesCsv(desired), 'utf8');
    fs.writeFileSync(path.join(OUT,'source-live-at-apply.json'), JSON.stringify(source,null,2));
    fs.writeFileSync(path.join(OUT,'desired-messages.json'), JSON.stringify(desired,null,2));

    await page.getByRole('button', {name:'New Broadcast Template'}).click();
    await page.waitForTimeout(800);
    const parent = page.locator('.modal-content:visible').last();
    await parent.locator('#NAME').fill(TARGET);
    await selectDropdown(page, parent, 'Select a company', source.COMPANY);
    await selectDropdown(page, parent, 'Select domain', source.PUBLISHER_ID.replace(`${source.COMPANY}_`,''));
    const languageOption = ({ES:'Spanish',EN:'English',DE:'German',PT:'Portuguese',FR:'French',IT:'Italian',TR:'Turkish',PL:'Polish'})[source.LANGUAGE] || source.LANGUAGE;
    await selectDropdown(page, parent, 'Select language', languageOption);
    await parent.locator('#UTM_CONTENT_MASK').fill(source.UTM_CONTENT_MASK || '');
    await parent.getByRole('button', {name:/0 Messages/}).click();
    await page.waitForTimeout(800);
    const messagesModal = page.locator('.modal-content:visible').last();
    await messagesModal.getByText('Import', {exact:true}).click();
    await page.waitForTimeout(400);
    const fileInput = messagesModal.locator('input[type="file"]');
    if (await fileInput.count()) {
      await fileInput.setInputFiles(csvPath);
    } else {
      const chooserPromise = page.waitForEvent('filechooser');
      await messagesModal.getByRole('button', {name:/Upload/}).click();
      const chooser = await chooserPromise;
      await chooser.setFiles(csvPath);
    }
    await messagesModal.getByText('Uploaded messages: 30', {exact:false}).waitFor({timeout:30000});
    await messagesModal.getByText('Total messages: 30', {exact:false}).waitFor({timeout:30000});
    await messagesModal.getByRole('button', {name:'Update', exact:true}).click();
    await page.waitForTimeout(700);
    const parentAfterUpdate = page.locator('.modal-content:visible').last();
    await parentAfterUpdate.getByRole('button', {name:/30 Messages/}).waitFor({timeout:10000});
    await page.screenshot({path:path.join(OUT,'before-save.png'), fullPage:false});

    await parentAfterUpdate.getByRole('button', {name:'Save', exact:true}).click();
    await page.waitForTimeout(5000);
    await page.screenshot({path:path.join(OUT,'after-save.png'), fullPage:false});
    const toastText = await page.locator('.toast:visible, .p-toast:visible, [role="alert"]:visible').allInnerTexts().catch(()=>[]);
    fs.writeFileSync(path.join(OUT,'write-responses.json'), JSON.stringify({writeResponses,toastText}, null, 2));

    const liveRows = await fetchRows(context, listUrl, headers);
    const liveTargets = liveRows.filter(r=>r.NAME===TARGET);
    if (liveTargets.length !== 1) throw new Error(`readback target count ${liveTargets.length}; writes=${JSON.stringify(writeResponses)}; alerts=${JSON.stringify(toastText)}`);
    const target = liveTargets[0];
    const matchingWrite = [...writeResponses].reverse().find(x=>x.url.toLowerCase().includes('/broadcast/'));
    const saveStatus = matchingWrite ? matchingWrite.http : null;
    const targetMessages = parseMessages(target);
    const expectedCanonical = desired.map(canonicalMessage);
    const actualCanonical = targetMessages.map(canonicalMessage);
    const checks = {
      distinct_id: target.ID !== source.ID,
      exact_name: target.NAME === TARGET,
      company: target.COMPANY === source.COMPANY,
      publisher_id: target.PUBLISHER_ID === source.PUBLISHER_ID,
      language: target.LANGUAGE === source.LANGUAGE,
      utm_content_mask: (target.UTM_CONTENT_MASK || '') === (source.UTM_CONTENT_MASK || ''),
      message_count_30: targetMessages.length === 30,
      no_g004_links: countMedium(targetMessages,'g004-d') === 0,
      g001_links_30: countMedium(targetMessages,'g001-d') === 30,
      content_and_urls_exact: JSON.stringify(actualCanonical) === JSON.stringify(expectedCanonical),
      pages_zero: Number(target.PAGES || 0) === 0,
      leads_zero: Number(target.LEADS || 0) === 0,
    };
    fs.writeFileSync(path.join(OUT,'target-live-readback.json'), JSON.stringify(target,null,2));
    fs.writeFileSync(path.join(OUT,'validation.json'), JSON.stringify({source_id:source.ID,target_id:target.ID,save_http:saveStatus,checks},null,2));
    const failed = Object.entries(checks).filter(([,ok])=>!ok).map(([k])=>k);
    if (failed.length) throw new Error(`readback validation failed: ${failed.join(', ')}`);
    console.log(JSON.stringify({status:'OK',source:SOURCE,target:TARGET,source_id:source.ID,target_id:target.ID,save_http:saveStatus,messages:targetMessages.length,g001_links:countMedium(targetMessages,'g001-d'),g004_links:countMedium(targetMessages,'g004-d'),pages:target.PAGES,leads:target.LEADS,validation:path.join(OUT,'validation.json')},null,2));
  } finally { await browser.close(); }
})().catch(err=>{console.error(err.stack||String(err));process.exit(1);});
