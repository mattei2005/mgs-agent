'use strict';

const { chromium } = require('/root/mgs-agent/tools/meta-library-collector/node_modules/playwright');
const { resolveProxyConfig } = require('/root/mgs-agent/tools/meta-library-collector/proxy-config');
const fs = require('fs');
const cp = require('child_process');

const BUSINESS_ID = '155263197283282';
const BUSINESS_NAME = 'Digital Trust';
const BASE_URL = `https://business.facebook.com/latest/settings/ad_accounts?business_id=${BUSINESS_ID}`;
const PROFILE = '/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium';
const STATE_PATH = process.env.MGS_META_HOURLY_STATE || '/root/mgs-agent/data/meta-digital-trust-hourly40-20260906-state.json';
const MODE = process.argv.includes('--preflight') ? 'preflight' : 'create-one';
let context = null;

function now() { return new Date().toISOString(); }
function emit(value) { process.stdout.write(JSON.stringify(value) + '\n'); }
function runtimeUa() {
  let major = '149';
  try {
    const result = cp.execFileSync(chromium.executablePath(), ['--version'], { encoding: 'utf8', timeout: 5000 });
    const match = result.match(/(\d+)\./);
    if (match) major = match[1];
  } catch (_) {}
  return `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${major}.0.0.0 Safari/537.36`;
}
function readState() { return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8')); }
async function bodyText(page) { return await page.locator('body').innerText({ timeout: 30000 }); }
async function htmlPayloadIds(page) {
  const html = await page.content();
  return [...new Set([...html.matchAll(/business_object_ui_id.{0,80}?["']?(\d{10,})/g)].map(m => m[1]))];
}
function classifyGate(pageUrl, text) {
  if (pageUrl.includes('/security/twofactor/reauth/') || /2FA Entry|Confirm it's you with your passkey|Try another way/i.test(text)) return 'reauth_required';
  if (/Log into Facebook|Log in to Facebook|Enter your password/i.test(text)) return 'login_required';
  if (/checkpoint|security check|confirm your identity|unusual activity/i.test(text)) return 'security_gate';
  return null;
}
async function ensureBase(page) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);
  const text = await bodyText(page);
  const gate = classifyGate(page.url(), text);
  if (gate) throw new Error(gate);
  if (!page.url().includes(`business_id=${BUSINESS_ID}`)) throw new Error('target_url_drift');
  if (!text.includes(BUSINESS_NAME) || !text.includes('Ad accounts')) throw new Error('target_structure_missing');
  const add = page.getByText('Add', { exact: true });
  if (await add.count() !== 1) throw new Error(`add_button_count_${await add.count()}`);
  return text;
}
async function openCreateDialog(page) {
  const add = page.getByText('Add', { exact: true });
  await add.click({ timeout: 30000 });
  await page.waitForTimeout(700);
  const createMenu = page.getByText('Create a new ad account', { exact: true });
  await createMenu.waitFor({ state: 'visible', timeout: 15000 });
  if (await createMenu.count() !== 1) throw new Error(`create_menu_count_${await createMenu.count()}`);
  await createMenu.click();
  const dialog = page.getByRole('dialog');
  await dialog.waitFor({ state: 'visible', timeout: 30000 });
  const text = await dialog.innerText();
  if (/maximum number of ad accounts|reached the maximum/i.test(text)) throw new Error('maximum_account_gate');
  if (!text.includes('Create a new ad account for this portfolio')) throw new Error('details_dialog_mismatch');
  return dialog;
}
async function validateAccount(page, selectedAssetId, expectedId = null) {
  if (!selectedAssetId) throw new Error('selected_asset_id_missing');
  const url = `${BASE_URL}&selected_asset_id=${selectedAssetId}&selected_asset_type=ad-account`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForFunction((id) => {
    const text = document.body ? document.body.innerText : '';
    return /ID:\s*\d{10,}/.test(text) && text.includes('Owned by: Digital Trust') && (!id || text.includes(`ID: ${id}`));
  }, expectedId, { timeout: 60000 });
  const details = await bodyText(page);
  const gate = classifyGate(page.url(), details);
  if (gate) throw new Error(gate);
  const ids = [...new Set([...details.matchAll(/ID:\s*(\d{10,})/g)].map(m => m[1]))];
  if (ids.length !== 1) throw new Error(`id_readback_count_${ids.length}`);
  const id = ids[0];
  if (expectedId && id !== expectedId) throw new Error('id_readback_mismatch');
  if (!/Owned by:\s*Digital Trust/.test(details)) throw new Error('owner_readback_mismatch');
  if (!/(?:^|\n)001(?:\n|$)/.test(details)) throw new Error('name_readback_mismatch');
  const peopleTab = page.getByRole('tab', { name: 'People', exact: true });
  if (await peopleTab.count() !== 1) throw new Error(`people_tab_count_${await peopleTab.count()}`);
  await peopleTab.click();
  await page.waitForFunction(() => {
    const text = document.body ? document.body.innerText : '';
    return /1 person is assigned to this ad account/i.test(text) && text.includes('Rodolfo Mattei (You)') && text.includes('Full access');
  }, null, { timeout: 45000 });
  const people = await bodyText(page);
  return {
    id,
    selected_asset_id: selectedAssetId,
    owner: BUSINESS_NAME,
    assigned_people: 1,
    rodolfo_full_access: /Rodolfo Mattei \(You\)[\s\S]{0,500}Full access/.test(people),
    name: '001',
    timezone: 'America/Los_Angeles',
    currency: 'USD',
    usage: 'My business',
    payment_method_added: false,
  };
}
async function reconcileAfterMutationError(page, beforeIds, state, reason) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  const text = await bodyText(page);
  const gate = classifyGate(page.url(), text);
  if (gate) return { kind: 'blocked', reason: gate, side_effect: 'unknown' };
  const known = new Set([...beforeIds, ...(state.preexisting_ids || []), ...(state.completed || []).map(x => x.id)]);
  const rows = page.getByRole('row');
  const candidates = [];
  for (let i = 0; i < await rows.count(); i++) {
    const row = rows.nth(i);
    const rowText = (await row.innerText().catch(() => '')).trim();
    if (!/^001(?:\n|$)/.test(rowText)) continue;
    await row.getByRole('button').first().click().catch(() => row.click());
    await page.waitForTimeout(600);
    const selected = await bodyText(page);
    const ids = [...new Set([...selected.matchAll(/ID:\s*(\d{10,})/g)].map(m => m[1]))];
    if (ids.length !== 1 || !/Owned by:\s*Digital Trust/.test(selected)) continue;
    const id = ids[0];
    if (!known.has(id)) {
      let assetId = null;
      try { assetId = new URL(page.url()).searchParams.get('selected_asset_id'); } catch (_) {}
      candidates.push({ id, selected_asset_id: assetId });
    }
  }
  const unique = [...new Map(candidates.map(x => [x.id, x])).values()];
  if (unique.length === 1) {
    const verified = await validateAccount(page, unique[0].selected_asset_id, unique[0].id);
    return { kind: 'created_reconciled', reason, account: verified };
  }
  if (unique.length === 0) return { kind: 'mutation_error_no_side_effect', reason };
  return { kind: 'ambiguous_multiple_new_ids', reason, candidate_count: unique.length };
}
async function createOne(page, state) {
  await ensureBase(page);
  const beforeIds = await htmlPayloadIds(page);
  let dialog = await openCreateDialog(page);
  const nameInputs = dialog.locator('input[type="text"]');
  if (await nameInputs.count() !== 1) throw new Error(`name_input_count_${await nameInputs.count()}`);
  await nameInputs.fill('001');
  const combos = dialog.getByRole('combobox');
  if (await combos.count() !== 2) throw new Error(`combobox_count_${await combos.count()}`);
  await combos.nth(0).click();
  const tzSearch = page.locator('input').last();
  await tzSearch.fill('America/Los_Angeles');
  await page.waitForTimeout(500);
  const tzOption = page.getByRole('option', { name: /America\/Los Angeles/ });
  if (await tzOption.count() !== 1) throw new Error(`timezone_option_count_${await tzOption.count()}`);
  await tzOption.click();
  let dialogText = await dialog.innerText();
  if (!dialogText.includes('America/Los Angeles') || !dialogText.includes('USD — US Dollars')) throw new Error('details_readback_mismatch');
  if (await nameInputs.inputValue() !== '001') throw new Error('name_readback_mismatch');
  const next1 = dialog.getByRole('button', { name: 'Next', exact: true });
  if (await next1.isDisabled()) throw new Error('details_next_disabled');
  await next1.click();
  await page.waitForTimeout(500);
  dialog = page.getByRole('dialog');
  dialogText = await dialog.innerText();
  if (!dialogText.includes('Select who will use this ad account') || !dialogText.includes('My business')) throw new Error('usage_dialog_mismatch');
  await dialog.getByText('My business', { exact: true }).click();
  const next2 = dialog.getByRole('button', { name: 'Next', exact: true });
  if (await next2.isDisabled()) throw new Error('usage_next_disabled');
  await next2.click();
  await page.waitForTimeout(500);
  dialog = page.getByRole('dialog');
  dialogText = await dialog.innerText();
  if (!dialogText.includes('Confirm the ad account you want to create') || !dialogText.includes(BUSINESS_NAME) || !dialogText.includes('001')) throw new Error('confirm_dialog_mismatch');
  const checkbox = dialog.locator('input[type="checkbox"]');
  if (await checkbox.count() !== 1) throw new Error(`terms_checkbox_count_${await checkbox.count()}`);
  await checkbox.check({ force: true });
  const createButton = dialog.getByRole('button', { name: 'Create ad account', exact: true });
  if (await createButton.isDisabled()) throw new Error('create_button_disabled_after_terms');
  const clickedAt = now();
  await createButton.click();
  let outcome;
  try {
    outcome = await page.waitForFunction(() => {
      const text = document.body ? document.body.innerText : '';
      if (/Ad account created successfully|Ad account created/i.test(text)) return { kind: 'success' };
      const match = text.match(/Unable to add ad account[^\n]*|maximum number of ad accounts[^\n]*|Network request timed out[^\n]*|Error performing query[^\n]*|unusual activity[^\n]*|security check[^\n]*/i);
      if (match) return { kind: 'error', reason: match[0] };
      return null;
    }, null, { timeout: 90000 }).then(h => h.jsonValue());
  } catch (_) {
    return await reconcileAfterMutationError(page, beforeIds, state, 'mutation_timeout_or_blank');
  }
  if (!outcome || outcome.kind !== 'success') {
    return await reconcileAfterMutationError(page, beforeIds, state, String(outcome && outcome.reason || 'unknown_mutation_error').slice(0, 200));
  }
  let selectedAssetId = null;
  try { selectedAssetId = new URL(page.url()).searchParams.get('selected_asset_id'); } catch (_) {}
  if (!selectedAssetId) return await reconcileAfterMutationError(page, beforeIds, state, 'success_without_selected_asset_id');
  const done = dialog.getByRole('button', { name: 'Done', exact: true });
  await done.waitFor({ state: 'visible', timeout: 30000 });
  await done.click();
  const verified = await validateAccount(page, selectedAssetId, null);
  return { kind: 'created', clicked_at: clickedAt, account: verified };
}
async function main() {
  const state = readState();
  const proxy = resolveProxyConfig();
  context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    userAgent: runtimeUa(),
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage', '--lang=en-US,en'],
    proxy: proxy.playwrightProxy,
    env: proxy.browserEnv,
  });
  const page = context.pages()[0] || await context.newPage();
  page.setDefaultTimeout(30000);
  if (MODE === 'preflight') {
    await ensureBase(page);
    const dialog = await openCreateDialog(page);
    const text = await dialog.innerText();
    await page.keyboard.press('Escape').catch(() => {});
    emit({ kind: 'preflight_ok', business_id: BUSINESS_ID, business_name: BUSINESS_NAME, create_form: true, maximum_gate: /maximum number of ad accounts/i.test(text) });
  } else {
    const result = await createOne(page, state);
    emit(result);
  }
  await context.close();
  context = null;
}
async function stop() { try { if (context) await context.close(); } catch (_) {} process.exit(143); }
process.once('SIGTERM', stop);
process.once('SIGINT', stop);
main().catch(async error => {
  try { if (context) await context.close(); } catch (_) {}
  const message = String(error && error.message || error).slice(0, 200);
  const known = new Set(['reauth_required','login_required','security_gate','maximum_account_gate','target_url_drift','target_structure_missing']);
  emit({ kind: known.has(message) ? 'blocked' : 'failed_prewrite_or_validation', reason: message });
  process.exit(0);
});
