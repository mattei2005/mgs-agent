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

function secret(field) {
  return cp.execFileSync('op', ['item', 'get', 'Zeus - Smartbidding Dashboard', '--vault', 'MGS Conteúdo', '--field', field, '--reveal'], {encoding:'utf8'}).trim();
}

async function loginIfNeeded(page, context) {
  const body = await page.locator('body').innerText({timeout: 15000});
  if (!body.includes('Log in to Smart Bidding') && !body.includes('Email address')) return false;
  await page.locator('input[type="email"]:visible, input[name="username"]:visible, input[name="email"]:visible, input:visible').first().fill(secret('username'));
  await page.locator('input[type="password"]:visible').first().fill(secret('password'));
  await page.getByRole('button', {name:/Continue|Log in|Login/i}).first().click();
  await page.waitForLoadState('networkidle', {timeout:90000});
  await page.waitForTimeout(3000);
  await context.storageState({path:STATE});
  return true;
}

(async () => {
  fs.mkdirSync(OUT, {recursive:true});
  const browser = await chromium.launch({headless:false, args:['--disable-blink-features=AutomationControlled']});
  const context = await browser.newContext({storageState: fs.existsSync(STATE) ? STATE : undefined, viewport:{width:1600,height:1000}, userAgent:UA});
  const page = await context.newPage();
  const captured = [];
  let headers = null;
  let postUrl = 'https://api.jbfdigital.com.br/broadcast/Messenger';
  page.on('request', req => {
    if (req.url().includes('/broadcast/Messenger') && req.method() === 'GET') {
      headers = req.headers();
      postUrl = req.url().split('?')[0];
    }
  });
  page.on('response', async resp => {
    if (resp.url().includes('/broadcast/Messenger') && resp.status() === 200) {
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
    const dedup = new Map(); for (const row of captured) dedup.set(row.ID || row.NAME, row);
    const rows = [...dedup.values()];
    const sources = rows.filter(r => r.NAME === SOURCE);
    const targets = rows.filter(r => r.NAME === TARGET);
    if (sources.length !== 1) throw new Error(`exact source count ${sources.length}`);
    const source = sources[0];
    fs.writeFileSync(path.join(OUT, 'source-live-before.json'), JSON.stringify(source, null, 2));
    const msgs = typeof source.MESSAGES === 'string' ? JSON.parse(source.MESSAGES) : (source.MESSAGES || []);
    const links = []; for (const m of msgs) for (const k of ['LINK_1','LINK_2']) if (m[k]) links.push(m[k]);
    const buttons = await page.getByRole('button').allInnerTexts();
    await page.getByRole('button', {name:'New Broadcast Template'}).click();
    await page.waitForTimeout(1200);
    const dialogs = await page.locator('.p-dialog').allInnerTexts();
    const inputs = await page.locator('input:visible, textarea:visible').evaluateAll(nodes => nodes.map((n,i) => ({i, tag:n.tagName, type:n.type || '', name:n.name || '', placeholder:n.placeholder || '', value:n.value || '', aria:n.getAttribute('aria-label') || '', outer:n.outerHTML.slice(0,500)})));
    const dropdowns = await page.locator('.p-dropdown:visible').evaluateAll(nodes => nodes.map((n,i)=>({i,text:n.innerText,outer:n.outerHTML.slice(0,700)})));
    await page.screenshot({path:path.join(OUT, 'new-template-modal.png'), fullPage:false});
    await page.getByRole('button', {name:/0 Messages/}).click();
    await page.waitForTimeout(1000);
    await page.screenshot({path:path.join(OUT, 'messages-modal.png'), fullPage:false});
    const modalTexts = await page.locator('.modal-content:visible, .p-dialog:visible, [role="dialog"]:visible').allInnerTexts();
    const visibleInputsAfterMessages = await page.locator('input:visible, textarea:visible').evaluateAll(nodes => nodes.map((n,i)=>({i,type:n.type||'',id:n.id||'',placeholder:n.placeholder||'',value:n.value||'',accept:n.accept||''})));
    const visibleButtons = await page.getByRole('button').filter({visible:true}).allInnerTexts().catch(() => []);
    console.log(JSON.stringify({
      source_found:sources.length, target_found:targets.length, source_id:source.ID,
      source_company:source.COMPANY, source_publisher_id:source.PUBLISHER_ID,
      source_language:source.LANGUAGE, source_pages:source.PAGES, source_leads:source.LEADS,
      message_count:msgs.length, link_count:links.length,
      g004_link_count:links.filter(x=>x.includes('utm_medium=g004-d')).length,
      g001_link_count:links.filter(x=>x.includes('utm_medium=g001-d')).length,
      field_keys:Object.keys(source).sort(), buttons, dialogs, inputs, dropdowns, modalTexts, visibleInputsAfterMessages, visibleButtons, post_url:postUrl,
      modal_screenshot:path.join(OUT, 'new-template-modal.png'),
      messages_screenshot:path.join(OUT, 'messages-modal.png'),
      auth_headers_captured:!!headers,
      backup:path.join(OUT, 'source-live-before.json')
    }, null, 2));
  } finally { await browser.close(); }
})().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
