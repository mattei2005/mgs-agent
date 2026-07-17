#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');
const { resolveProxyConfig } = require('./proxy-config');

function validateUrl(raw) {
  const parsed = new URL(raw);
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'www.facebook.com' || !parsed.pathname.startsWith('/ads/library/')) {
    throw new Error('URL permitida: https://www.facebook.com/ads/library/...');
  }
  for (const key of parsed.searchParams.keys()) {
    if (/(access_token|token|authorization|password|cookie)/i.test(key)) throw new Error(`Parâmetro sensível recusado: ${key}`);
  }
  return parsed.toString();
}

function runtimeUa() {
  let major = '149';
  try {
    const output = childProcess.execFileSync(chromium.executablePath(), ['--version'], { encoding: 'utf8', timeout: 5000 });
    const match = output.match(/(\d+)\.\d+\.\d+\.\d+/);
    if (match) major = match[1];
  } catch (_) {}
  return `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${major}.0.0.0 Safari/537.36`;
}

async function main() {
  const url = validateUrl(process.argv[2] || 'https://www.facebook.com/ads/library/');
  const profileDir = process.env.ARES_META_LIBRARY_PROFILE || '/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium';
  const statusPath = process.env.ARES_META_LIBRARY_LOGIN_STATUS || '/root/.hermes/profiles/ares/artifacts/meta-library-login-status.json';
  fs.mkdirSync(profileDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(path.dirname(statusPath), { recursive: true, mode: 0o700 });

  const proxy = resolveProxyConfig();
  const launchOptions = {
    headless: false,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    userAgent: runtimeUa(),
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage', '--lang=en-US,en'],
    proxy: proxy.playwrightProxy,
    env: proxy.browserEnv
  };
  const context = await chromium.launchPersistentContext(profileDir, launchOptions);
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  });

  const page = context.pages()[0] || await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => null);
  const writeStatus = async state => {
    const cookies = await context.cookies(['https://www.facebook.com']).catch(() => []);
    const names = new Set(cookies.map(cookie => cookie.name));
    const status = {
      state,
      updatedAt: new Date().toISOString(),
      profileDir,
      pageTitle: await page.title().catch(() => null),
      authenticatedLikely: names.has('c_user') && names.has('xs'),
      proxyMode: proxy.mode
    };
    fs.writeFileSync(statusPath, JSON.stringify(status, null, 2) + '\n', { mode: 0o600 });
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
  process.stderr.write(`login-browser error: ${String(error.message || error).slice(0, 500)}\n`);
  process.exit(1);
});
