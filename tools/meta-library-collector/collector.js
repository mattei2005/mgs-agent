#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const childProcess = require('child_process');
const { resolveProxyConfig } = require('./proxy-config');

let activeContext = null;

async function closeActiveContext() {
  if (!activeContext) return;
  const context = activeContext;
  activeContext = null;
  try { await context.close(); } catch (_) {}
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, async () => {
    await closeActiveContext();
    process.exit(128 + (signal === 'SIGINT' ? 2 : 15));
  });
}

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) continue;
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      out[key] = next;
      i++;
    } else {
      out[key] = true;
    }
  }
  return out;
}

function intArg(value, fallback, min, max) {
  const parsed = Number.parseInt(value ?? '', 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

function boolArg(value, fallback) {
  if (value === undefined) return fallback;
  return !['0', 'false', 'no', 'off'].includes(String(value).toLowerCase());
}

function safeTimestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function validateSourceUrl(raw) {
  let parsed;
  try { parsed = new URL(raw); } catch (_) { throw new Error('URL inválida.'); }
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'www.facebook.com' || !parsed.pathname.startsWith('/ads/library/')) {
    throw new Error('Use uma URL https://www.facebook.com/ads/library/ válida.');
  }
  const forbidden = ['access_token', 'token', 'authorization', 'password', 'cookie'];
  for (const key of parsed.searchParams.keys()) {
    if (forbidden.some(term => key.toLowerCase().includes(term))) {
      throw new Error(`Parâmetro sensível recusado na URL: ${key}`);
    }
  }
  return parsed.toString();
}

function chromiumVersionAndUa() {
  let version = 'unknown';
  let major = '149';
  try {
    const output = childProcess.execFileSync(chromium.executablePath(), ['--version'], { encoding: 'utf8', timeout: 5000 }).trim();
    const match = output.match(/(\d+)\.\d+\.\d+\.\d+/);
    if (match) {
      version = match[0];
      major = match[1];
    }
  } catch (_) {}
  return {
    version,
    userAgent: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${major}.0.0.0 Safari/537.36`
  };
}

function detectMediaType(contentType, body) {
  const mime = String(contentType || '').split(';')[0].trim().toLowerCase();
  const jpeg = body.length >= 3 && body[0] === 0xff && body[1] === 0xd8 && body[2] === 0xff;
  const png = body.length >= 8 && body.subarray(0, 8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]));
  const webp = body.length >= 12 && body.subarray(0, 4).toString('ascii') === 'RIFF' && body.subarray(8, 12).toString('ascii') === 'WEBP';
  const mp4 = body.length >= 12 && body.subarray(4, 8).toString('ascii') === 'ftyp';
  if (mime === 'image/jpeg' && jpeg) return { extension: '.jpg', kind: 'image' };
  if (mime === 'image/png' && png) return { extension: '.png', kind: 'image' };
  if (mime === 'image/webp' && webp) return { extension: '.webp', kind: 'image' };
  if (mime === 'video/mp4' && mp4) return { extension: '.mp4', kind: 'video' };
  return null;
}

async function extractSnapshot(page) {
  return page.evaluate(() => {
    const text = document.body ? document.body.innerText : '';
    const html = document.documentElement ? document.documentElement.outerHTML : '';
    const libraryIds = [...new Set([...text.matchAll(/Library ID:\s*(\d+)/gi)].map(match => match[1]))];
    const nearestLibraryId = element => {
      let current = element;
      for (let depth = 0; current && depth < 10; depth++, current = current.parentElement) {
        const candidate = current.innerText || '';
        const match = candidate.match(/Library ID:\s*(\d+)/i);
        if (match) return match[1];
      }
      return null;
    };
    const acceptedUrl = src => {
      if (!src || src.startsWith('data:') || src.startsWith('blob:')) return false;
      try { return new URL(src).hostname.includes('fbcdn.net'); } catch (_) { return false; }
    };
    const images = [...document.images]
      .map(img => ({ kind: 'image', src: img.currentSrc || img.src, width: img.naturalWidth, height: img.naturalHeight, alt: img.alt || '', libraryId: nearestLibraryId(img) }))
      .filter(item => acceptedUrl(item.src) && item.width >= 200 && item.height >= 100);
    const videos = [...document.querySelectorAll('video')]
      .map(video => ({ kind: 'video', src: video.currentSrc || video.src, width: video.videoWidth, height: video.videoHeight, alt: '', libraryId: nearestLibraryId(video) }))
      .filter(item => acceptedUrl(item.src) && item.width > 0 && item.height > 0);
    const resultMatch = text.match(/~?[\d,.]+\s+results?/i);
    return {
      title: document.title,
      location: location.href,
      textLength: text.length,
      resultText: resultMatch ? resultMatch[0] : null,
      libraryIds,
      media: [...images, ...videos],
      markers: {
        adLibrary: /Ad Library/i.test(text) || /ads\/library/i.test(html),
        activeAds: /Active ads/i.test(text),
        loginPrompt: /Log in|Create new account/i.test(text),
        challenge: /__rd_verify|executeChallenge/i.test(html),
        captcha: /captcha/i.test(html),
        noResults: /No ads match|No results found/i.test(text)
      }
    };
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const url = validateSourceUrl(args.url || '');
  const profileDir = path.resolve(args.profile || process.env.ARES_META_LIBRARY_PROFILE || '/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium');
  const outputRoot = path.resolve(args['output-root'] || process.env.ARES_META_LIBRARY_OUTPUT || '/root/.hermes/profiles/ares/artifacts/meta-library');
  const runDir = path.join(outputRoot, safeTimestamp());
  const scrolls = intArg(args.scrolls, 20, 0, 100);
  const waitMs = intArg(args['wait-ms'], 1500, 250, 10000);
  const downloadLimit = intArg(args.download, 1, 0, 100);
  const headless = boolArg(args.headless, true);
  const minUsefulIds = intArg(args['min-ids'], 3, 3, 100);
  const minBytes = intArg(args['min-bytes'], 2048, 512, 1048576);
  const maxBytes = intArg(args['max-bytes'], 50 * 1024 * 1024, 1024 * 1024, 200 * 1024 * 1024);

  const profileReused = fs.existsSync(path.join(profileDir, 'Default'));
  fs.mkdirSync(profileDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(runDir, { recursive: true, mode: 0o700 });
  fs.chmodSync(profileDir, 0o700);
  fs.chmodSync(runDir, 0o700);
  fs.writeFileSync(path.join(profileDir, 'README-MGS.txt'), [
    'Perfil persistente do Ares para Meta/Facebook Ads Library.',
    'NÃO APAGAR: pode conter cookies/sessão de login do Rodolfo.',
    'Não versionar, copiar para o Discord ou inspecionar valores de cookies.',
    'Runtime canônico: /root/mgs-agent/tools/meta-library-collector/',
    ''
  ].join('\n'), { mode: 0o600 });

  const runtime = chromiumVersionAndUa();
  const proxy = resolveProxyConfig();
  const launchOptions = {
    headless,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    userAgent: runtime.userAgent,
    extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage', '--lang=en-US,en'],
    proxy: proxy.playwrightProxy,
    env: proxy.browserEnv
  };
  const context = await chromium.launchPersistentContext(profileDir, launchOptions);
  activeContext = context;

  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  });

  const page = context.pages()[0] || await context.newPage();
  const responseSummary = [];
  page.on('response', response => {
    const responseUrl = response.url();
    if ((responseUrl.includes('facebook.com') || responseUrl.includes('fbcdn.net')) && responseSummary.length < 500) {
      responseSummary.push({
        host: (() => { try { return new URL(responseUrl).host; } catch (_) { return ''; } })(),
        status: response.status(),
        contentType: response.headers()['content-type'] || ''
      });
    }
  });

  let gotoStatus = null;
  let gotoError = null;
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    gotoStatus = response ? response.status() : null;
  } catch (error) {
    gotoError = String(error.message || error).slice(0, 500);
  }

  const allIds = new Set();
  const allMedia = new Map();
  let latest = null;
  let initialIdCount = 0;
  const mergeSnapshot = snapshot => {
    latest = snapshot;
    for (const id of snapshot.libraryIds) allIds.add(id);
    for (const item of snapshot.media) if (!allMedia.has(item.src)) allMedia.set(item.src, item);
  };

  for (let attempt = 0; attempt < 15; attempt++) {
    await page.waitForTimeout(3000);
    mergeSnapshot(await extractSnapshot(page));
    if (allIds.size >= minUsefulIds || latest.markers.noResults) break;
  }
  initialIdCount = allIds.size;

  let scrollsPerformed = 0;
  let stableRounds = 0;
  for (let i = 0; i < scrolls; i++) {
    const before = `${allIds.size}:${allMedia.size}`;
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(waitMs);
    mergeSnapshot(await extractSnapshot(page));
    scrollsPerformed += 1;
    const after = `${allIds.size}:${allMedia.size}`;
    stableRounds = after === before ? stableRounds + 1 : 0;
    if (stableRounds >= 4) break;
  }

  const cookies = await context.cookies(['https://www.facebook.com']);
  const cookieNames = new Set(cookies.map(cookie => cookie.name));
  const authenticatedCookieNamesPresent = ['c_user', 'xs'].filter(name => cookieNames.has(name));
  const screenshotPath = path.join(runDir, 'meta-library.png');
  await page.screenshot({ path: screenshotPath, fullPage: false });
  fs.chmodSync(screenshotPath, 0o600);

  const media = [...allMedia.values()];
  const downloads = [];
  const downloadCandidates = allIds.size >= minUsefulIds ? media.filter(item => item.libraryId && allIds.has(item.libraryId)) : [];
  const fallbackCandidates = downloadCandidates.length ? downloadCandidates : (allIds.size >= minUsefulIds ? media : []);

  for (const item of fallbackCandidates.slice(0, downloadLimit)) {
    try {
      const response = await context.request.get(item.src, { timeout: 60000, headers: { Referer: 'https://www.facebook.com/ads/library/' } });
      if (!response.ok()) throw new Error(`HTTP ${response.status()}`);
      const body = await response.body();
      if (body.length < minBytes || body.length > maxBytes) throw new Error(`Tamanho recusado: ${body.length} bytes`);
      const contentType = response.headers()['content-type'] || '';
      const detected = detectMediaType(contentType, body);
      if (!detected) throw new Error(`MIME/magic-byte recusado: ${contentType || 'ausente'}`);
      const filename = `media-${String(downloads.length + 1).padStart(3, '0')}${detected.extension}`;
      const outputPath = path.join(runDir, filename);
      const tempPath = `${outputPath}.tmp-${process.pid}`;
      fs.writeFileSync(tempPath, body, { mode: 0o600 });
      fs.renameSync(tempPath, outputPath);
      downloads.push({
        file: outputPath,
        status: response.status(),
        contentType: String(contentType).split(';')[0],
        bytes: body.length,
        sha256: sha256(body),
        width: item.width,
        height: item.height,
        kind: detected.kind,
        libraryId: item.libraryId || null,
        magicBytesValid: true
      });
    } catch (error) {
      downloads.push({ kind: item.kind, libraryId: item.libraryId || null, error: String(error.message || error).slice(0, 300) });
    }
  }

  const usefulIds = allIds.size >= minUsefulIds;
  const persistentChallenge = Boolean(latest && latest.markers.challenge && !usefulIds);
  const successfulDownloads = downloads.filter(item => !item.error && item.status >= 200 && item.status < 300).length;
  const success = Boolean(latest && latest.markers.adLibrary && usefulIds && media.length > 0 && !persistentChallenge && (downloadLimit === 0 || successfulDownloads > 0));

  const report = {
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    profileDir,
    runDir,
    runtime: { node: process.version, playwright: require('playwright/package.json').version, chromium: runtime.version },
    headless,
    proxyMode: proxy.mode,
    gotoStatus,
    gotoError,
    profile: { reused: profileReused, permissions: '0700' },
    page: {
      title: latest ? latest.title : null,
      location: latest ? latest.location : null,
      textLength: latest ? latest.textLength : 0,
      resultText: latest ? latest.resultText : null,
      markers: latest ? latest.markers : {},
      persistentChallenge,
      scrollsRequested: scrolls,
      scrollsPerformed,
      stoppedAfterStableRounds: stableRounds >= 4,
      initialLibraryIdCount: initialIdCount,
      libraryIdCount: allIds.size,
      libraryIds: [...allIds],
      imageCount: media.filter(item => item.kind === 'image').length,
      videoCount: media.filter(item => item.kind === 'video').length,
      mediaLinkedToCardCount: media.filter(item => item.libraryId).length
    },
    session: {
      facebookCookieCount: cookies.length,
      authenticatedCookieNamesPresent,
      authenticatedLikely: authenticatedCookieNamesPresent.length === 2
    },
    downloads,
    network: {
      observed: responseSummary.length,
      status200: responseSummary.filter(item => item.status === 200).length,
      fbcdn200: responseSummary.filter(item => item.status === 200 && item.host.includes('fbcdn.net')).length
    },
    screenshot: screenshotPath,
    success
  };

  const reportPath = path.join(runDir, 'report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), { mode: 0o600 });
  await closeActiveContext();

  process.stdout.write(JSON.stringify({
    success,
    reportPath,
    profileDir,
    profileReused,
    gotoStatus,
    resultText: report.page.resultText,
    initialLibraryIdCount: initialIdCount,
    libraryIdCount: allIds.size,
    imageCount: report.page.imageCount,
    videoCount: report.page.videoCount,
    mediaLinkedToCardCount: report.page.mediaLinkedToCardCount,
    authenticatedLikely: report.session.authenticatedLikely,
    downloadCount: successfulDownloads
  }, null, 2) + '\n');
  if (!success) process.exitCode = 2;
}

main().catch(async error => {
  await closeActiveContext();
  process.stderr.write(JSON.stringify({ success: false, error: String(error.message || error).slice(0, 800) }, null, 2) + '\n');
  process.exit(1);
});
