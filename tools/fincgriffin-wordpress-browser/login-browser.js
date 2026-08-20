#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');

const ORIGIN = 'https://fincgriffin.com';
const DEFAULT_URL = `${ORIGIN}/wp-admin/`;
const PROFILE_DIR = process.env.FINCG_WP_PROFILE || '/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium';
const STATUS_PATH = process.env.FINCG_WP_STATUS || '/root/.hermes/profiles/zeus/artifacts/fincgriffin-wordpress-login-status.json';

function validateUrl(raw) {
  const parsed = new URL(raw);
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'fincgriffin.com') throw new Error('Only fincgriffin.com HTTPS URLs are allowed');
  if (!parsed.pathname.startsWith('/wp-admin') && parsed.pathname !== '/wp-login.php') throw new Error('Only WordPress admin/login paths are allowed');
  for (const key of parsed.searchParams.keys()) {
    if (/(access_token|token|authorization|password|cookie)/i.test(key)) throw new Error(`Sensitive URL parameter refused: ${key}`);
  }
  return parsed.toString();
}

function runtimeUa() {
  let major = '124';
  try {
    const output = childProcess.execFileSync(chromium.executablePath(), ['--version'], { encoding: 'utf8', timeout: 5000 });
    const match = output.match(/(\d+)\.\d+\.\d+\.\d+/);
    if (match) major = match[1];
  } catch (_) {}
  return `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${major}.0.0.0 Safari/537.36`;
}

async function main() {
  const url = validateUrl(process.argv[2] || DEFAULT_URL);
  fs.mkdirSync(PROFILE_DIR, { recursive: true, mode: 0o700 });
  fs.chmodSync(PROFILE_DIR, 0o700);
  fs.mkdirSync(path.dirname(STATUS_PATH), { recursive: true, mode: 0o700 });
  fs.writeFileSync(path.join(PROFILE_DIR, 'README-MGS-SESSION.txt'), 'Sensitive persistent Chromium profile for fincgriffin.com WordPress. Never copy, attach, commit, or delete while Chromium is running.\n', { mode: 0o600 });

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    userAgent: runtimeUa(),
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage', '--lang=en-US,en'],
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  });

  let page = context.pages()[0] || await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => null);

  const writeStatus = async (state) => {
    const pages = context.pages();
    page = pages[0] || page;
    const cookies = await context.cookies([ORIGIN]).catch(() => []);
    const names = new Set(cookies.map(cookie => cookie.name));
    const adminUiVisible = await page.locator('#wpadminbar').isVisible().catch(() => false);
    let currentPath = null;
    try {
      const current = new URL(page.url());
      if (current.hostname === 'fincgriffin.com') currentPath = current.pathname;
    } catch (_) {}
    const status = {
      state,
      updatedAt: new Date().toISOString(),
      profileDir: PROFILE_DIR,
      pageTitle: await page.title().catch(() => null),
      currentPath,
      adminUiVisible,
      authenticatedLikely: adminUiVisible || [...names].some(name => name.startsWith('wordpress_logged_in_')),
    };
    fs.writeFileSync(STATUS_PATH, JSON.stringify(status, null, 2) + '\n', { mode: 0o600 });
  };

  await writeStatus('ready');
  const timer = setInterval(() => writeStatus('ready').catch(() => null), 5000);
  let stopping = false;
  const stop = async () => {
    if (stopping) return;
    stopping = true;
    clearInterval(timer);
    await writeStatus('closing').catch(() => null);
    await context.close().catch(() => null);
    process.exit(0);
  };
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
  await new Promise(() => {});
}

main().catch(error => {
  process.stderr.write(`fincgriffin login-browser error: ${String(error.message || error).slice(0, 500)}\n`);
  process.exit(1);
});
