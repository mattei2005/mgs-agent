#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

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

function mediaExtension(contentType, url) {
  const type = String(contentType || '').toLowerCase();
  if (type.includes('image/jpeg')) return '.jpg';
  if (type.includes('image/png')) return '.png';
  if (type.includes('image/webp')) return '.webp';
  if (type.includes('video/mp4')) return '.mp4';
  try {
    const ext = path.extname(new URL(url).pathname).toLowerCase();
    if (['.jpg', '.jpeg', '.png', '.webp', '.mp4'].includes(ext)) return ext === '.jpeg' ? '.jpg' : ext;
  } catch (_) {}
  return '.bin';
}

async function main() {
  const args = parseArgs(process.argv);
  const url = args.url;
  if (!url || !/^https:\/\/(www\.)?facebook\.com\/ads\/library\//i.test(url)) {
    throw new Error('Use --url com uma URL https://www.facebook.com/ads/library/ válida.');
  }

  const profileDir = path.resolve(args.profile || process.env.HERA_META_LIBRARY_PROFILE || '/root/.hermes/profiles/hera/browser-profiles/meta-library-chromium');
  const outputRoot = path.resolve(args['output-root'] || process.env.HERA_META_LIBRARY_OUTPUT || '/root/.hermes/profiles/hera/artifacts/meta-library');
  const runDir = path.join(outputRoot, safeTimestamp());
  const scrolls = intArg(args.scrolls, 8, 0, 50);
  const waitMs = intArg(args['wait-ms'], 1500, 250, 10000);
  const downloadLimit = intArg(args.download, 1, 0, 100);
  const headless = boolArg(args.headless, true);

  fs.mkdirSync(profileDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(runDir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(path.join(profileDir, 'README-MGS.txt'), [
    'Perfil persistente da Hera para Meta/Facebook Ads Library.',
    'NÃO APAGAR: pode conter cookies/sessão de login do Rodolfo.',
    'Não versionar, copiar para o Discord ou inspecionar valores de cookies.',
    'Runtime canônico: /root/mgs-agent/tools/meta-library-collector/',
    ''
  ].join('\n'), { mode: 0o600 });

  const context = await chromium.launchPersistentContext(profileDir, {
    headless,
    viewport: { width: 1365, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--disable-features=IsolateOrigins,site-per-process',
      '--lang=en-US,en'
    ]
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = window.chrome || { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  });

  let page = context.pages()[0] || await context.newPage();
  const responseSummary = [];
  page.on('response', response => {
    const responseUrl = response.url();
    if ((responseUrl.includes('facebook.com') || responseUrl.includes('fbcdn.net')) && responseSummary.length < 300) {
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

  for (let i = 0; i < 4; i++) {
    await page.waitForTimeout(3000);
    const html = await page.content();
    if (!html.includes('/__rd_verify') && !html.toLowerCase().includes('executechallenge')) break;
  }

  try {
    await page.waitForFunction(() => {
      const text = document.body ? document.body.innerText : '';
      return /Library ID:\s*\d+/i.test(text) || /No ads match|No results found|0\s+results?/i.test(text);
    }, { timeout: 45000 });
  } catch (_) {}

  for (let i = 0; i < scrolls; i++) {
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(waitMs);
  }

  const data = await page.evaluate(() => {
    const text = document.body ? document.body.innerText : '';
    const html = document.documentElement ? document.documentElement.outerHTML : '';
    const images = [...document.images]
      .map(img => ({ kind: 'image', src: img.currentSrc || img.src, width: img.naturalWidth, height: img.naturalHeight, alt: img.alt || '' }))
      .filter(item => item.src && !item.src.startsWith('data:') && item.width >= 200 && item.height >= 100);
    const videos = [...document.querySelectorAll('video')]
      .map(video => ({ kind: 'video', src: video.currentSrc || video.src, width: video.videoWidth, height: video.videoHeight, alt: '' }))
      .filter(item => item.src && item.width > 0 && item.height > 0);
    const libraryIds = [...new Set([...text.matchAll(/Library ID:\s*(\d+)/gi)].map(match => match[1]))];
    const resultMatch = text.match(/~?[\d,.]+\s+results?/i);
    return {
      title: document.title,
      location: location.href,
      textLength: text.length,
      resultText: resultMatch ? resultMatch[0] : null,
      libraryIds,
      markers: {
        adLibrary: /Ad Library/i.test(text) || /ads\/library/i.test(html),
        libraryId: libraryIds.length > 0,
        noResults: /No ads match|No results found|0\s+results?/i.test(text),
        activeAds: /Active ads/i.test(text),
        loginPrompt: /Log in|Create new account/i.test(text),
        challenge: /__rd_verify|executeChallenge/i.test(html),
        captcha: /captcha/i.test(html)
      },
      media: [...images, ...videos]
    };
  });

  const cookies = await context.cookies(['https://www.facebook.com']);
  const cookieNames = new Set(cookies.map(cookie => cookie.name));
  const authenticatedCookieNamesPresent = ['c_user', 'xs'].filter(name => cookieNames.has(name));
  const screenshotPath = path.join(runDir, 'meta-library.png');
  await page.screenshot({ path: screenshotPath, fullPage: false });

  const uniqueMedia = [];
  const seen = new Set();
  for (const item of data.media) {
    if (seen.has(item.src)) continue;
    seen.add(item.src);
    uniqueMedia.push(item);
  }

  const downloads = [];
  const downloadCandidates = data.libraryIds.length > 0 ? uniqueMedia : [];
  for (const item of downloadCandidates.slice(0, downloadLimit)) {
    try {
      const response = await context.request.get(item.src, { timeout: 60000, headers: { Referer: 'https://www.facebook.com/ads/library/' } });
      const body = await response.body();
      const contentType = response.headers()['content-type'] || '';
      const extension = mediaExtension(contentType, item.src);
      const filename = `media-${String(downloads.length + 1).padStart(3, '0')}${extension}`;
      const outputPath = path.join(runDir, filename);
      fs.writeFileSync(outputPath, body, { mode: 0o600 });
      downloads.push({
        file: outputPath,
        status: response.status(),
        contentType,
        bytes: body.length,
        sha256: sha256(body),
        width: item.width,
        height: item.height,
        kind: item.kind
      });
    } catch (error) {
      downloads.push({ kind: item.kind, error: String(error.message || error).slice(0, 300) });
    }
  }

  const report = {
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    profileDir,
    runDir,
    headless,
    gotoStatus,
    gotoError,
    page: {
      title: data.title,
      location: data.location,
      textLength: data.textLength,
      resultText: data.resultText,
      markers: data.markers,
      libraryIds: data.libraryIds,
      imageCount: uniqueMedia.filter(item => item.kind === 'image').length,
      videoCount: uniqueMedia.filter(item => item.kind === 'video').length
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
    screenshot: screenshotPath
  };

  const reportPath = path.join(runDir, 'report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), { mode: 0o600 });
  await context.close();

  const success = data.markers.adLibrary && (data.libraryIds.length > 0 || data.markers.noResults);
  process.stdout.write(JSON.stringify({
    success,
    reportPath,
    profileDir,
    gotoStatus,
    resultText: data.resultText,
    libraryIdCount: data.libraryIds.length,
    imageCount: report.page.imageCount,
    videoCount: report.page.videoCount,
    authenticatedLikely: report.session.authenticatedLikely,
    downloadCount: downloads.filter(item => !item.error && item.status === 200).length
  }, null, 2) + '\n');
  if (!success) process.exitCode = 2;
}

main().catch(error => {
  process.stderr.write(JSON.stringify({ success: false, error: String(error.stack || error) }, null, 2) + '\n');
  process.exit(1);
});
