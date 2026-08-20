#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ORIGIN = 'https://fincgriffin.com';
const PROFILE_DIR = process.env.FINCG_WP_PROFILE || '/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium';
const STATUS_PATH = process.env.FINCG_WP_PROBE_STATUS || '/root/.hermes/profiles/zeus/artifacts/fincgriffin-wordpress-probe-status.json';

(async () => {
  fs.mkdirSync(PROFILE_DIR, { recursive: true, mode: 0o700 });
  fs.chmodSync(PROFILE_DIR, 0o700);
  fs.mkdirSync(path.dirname(STATUS_PATH), { recursive: true, mode: 0o700 });
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage', '--lang=en-US,en'],
  });
  try {
    const page = context.pages()[0] || await context.newPage();
    const response = await page.goto(`${ORIGIN}/wp-admin/`, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => null);
    const cookies = await context.cookies([ORIGIN]).catch(() => []);
    const names = new Set(cookies.map(cookie => cookie.name));
    const adminUiVisible = await page.locator('#wpadminbar').isVisible().catch(() => false);
    const authenticatedLikely = adminUiVisible || [...names].some(name => name.startsWith('wordpress_logged_in_'));
    const status = {
      state: authenticatedLikely ? 'authenticated' : 'not_authenticated',
      updatedAt: new Date().toISOString(),
      profileDir: PROFILE_DIR,
      initialHttp: response ? response.status() : null,
      pageTitle: await page.title().catch(() => null),
      adminUiVisible,
      authenticatedLikely,
    };
    fs.writeFileSync(STATUS_PATH, JSON.stringify(status, null, 2) + '\n', { mode: 0o600 });
    process.stdout.write(JSON.stringify(status) + '\n');
    if (!authenticatedLikely) process.exitCode = 4;
  } finally {
    await context.close().catch(() => null);
  }
})().catch(error => {
  process.stderr.write(`fincgriffin probe error: ${String(error.message || error).slice(0, 500)}\n`);
  process.exit(1);
});
