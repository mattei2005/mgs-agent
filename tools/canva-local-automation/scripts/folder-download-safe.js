const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
const SAFE_DIR = path.join(OUT_DIR, 'downloads_SAFE');
fs.mkdirSync(SAFE_DIR, { recursive: true });

function ask(q) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(r => rl.question(q, a => { rl.close(); r(a); }));
}
function safeName(s) {
  return (s || 'canva')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9._ -]+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 95) || 'canva';
}
function folderNameFromUrl(url, override) {
  if (override) return safeName(override);
  const m = String(url).match(/\/folder\/([^/?#]+)/);
  return m ? `folder_${m[1]}` : 'canva_folder';
}
function uniqueDest(dir, name, designId, ext) {
  return path.join(dir, `${safeName(name)}__${designId}${ext}`);
}
async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
}
async function closeModal(page) {
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(500);
}
async function collectVisible(page) {
  return await page.evaluate(() => {
    const out = [];
    const anchors = Array.from(document.querySelectorAll('a[href*="/design/editor/shell"]'));
    for (const a of anchors) {
      const rect = a.getBoundingClientRect();
      const name = (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
      const href = a.href;
      const m = href.match(/designId=([^&]+)/);
      if (!name || !m) continue;
      out.push({ name, href, designId: m[1], y: Math.round(rect.y), visible: rect.bottom > 0 && rect.top < innerHeight });
    }
    return out;
  });
}
async function collectAllByScrolling(page) {
  const seen = new Map();
  let stable = 0;
  await page.keyboard.press('Home').catch(() => {});
  await page.waitForTimeout(1000);
  for (let i = 0; i < 140; i++) {
    for (const it of await collectVisible(page)) seen.set(it.designId, it);
    const before = seen.size;
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(650);
    for (const it of await collectVisible(page)) seen.set(it.designId, it);
    stable = seen.size === before ? stable + 1 : 0;
    if (stable >= 7) break;
  }
  await page.keyboard.press('Home').catch(() => {});
  await page.waitForTimeout(1000);
  return Array.from(seen.values());
}
async function findAndOpenMoreByDesignId(page, designId) {
  await closeModal(page);
  await page.keyboard.press('Home').catch(() => {});
  await page.waitForTimeout(600);
  for (let i = 0; i < 160; i++) {
    const row = await page.evaluate((id) => {
      const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
      if (!a) return null;
      const r = a.getBoundingClientRect();
      if (r.bottom < 0 || r.top > innerHeight) return null;
      return { x: r.x, y: r.y, w: r.width, h: r.height };
    }, designId).catch(() => null);
    if (row) {
      const x = Math.min(row.x + row.w - 44, 1360);
      const y = row.y + Math.min(row.h / 2, 40);
      await page.mouse.move(x, y);
      await page.waitForTimeout(250);
      await page.mouse.click(x, y);
      await page.waitForTimeout(600);
      const txt = await bodyText(page);
      if (/\bBaixar\b/.test(txt) && /Copiar link|Compartilhar|Mover|Detalhes|Fazer uma cópia/.test(txt)) return true;
      // fallback: try visible more-actions button near this row
      const clicked = await page.evaluate((id) => {
        const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
        if (!a) return false;
        const ar = a.getBoundingClientRect();
        const btns = Array.from(document.querySelectorAll('button'));
        const candidates = btns.map(b => ({ b, r: b.getBoundingClientRect(), label: b.getAttribute('aria-label') || b.innerText || '' }))
          .filter(o => o.r.width > 20 && o.r.height > 20 && Math.abs((o.r.y + o.r.height / 2) - (ar.y + ar.height / 2)) < 20)
          .sort((a, b) => b.r.x - a.r.x);
        const more = candidates.find(o => /Mais ações|More actions|\.\.\./i.test(o.label)) || candidates[0];
        if (more) { more.b.click(); return true; }
        return false;
      }, designId).catch(() => false);
      if (clicked) {
        await page.waitForTimeout(600);
        const txt2 = await bodyText(page);
        if (/\bBaixar\b/.test(txt2)) return true;
      }
    }
    await page.mouse.wheel(0, 700);
    await page.waitForTimeout(450);
  }
  throw new Error(`Não achei botão Mais ações para designId=${designId}`);
}
async function clickDownloadMenu(page) {
  await page.getByText(/^Baixar$/).last().click({ timeout: 15000 });
}
async function getSelectedFormat(page) {
  await page.getByRole('button', { name: /Formato de arquivo/i }).waitFor({ timeout: 20000 }).catch(() => {});
  const txt = await bodyText(page);
  const formats = ['Vídeo MP4', 'Video MP4', 'PNG', 'JPG', 'PDF padrão', 'PDF para impressão', 'GIF'];
  for (const f of formats) if (txt.includes(f)) return f;
  return 'UNKNOWN';
}
async function clickFinalDownload(page) {
  const buttons = await page.locator('button').all();
  let target = null;
  for (const b of buttons) {
    const txt = (await b.innerText().catch(() => '')).trim();
    const box = await b.boundingBox().catch(() => null);
    if (txt === 'Baixar' && box && box.width > 150 && box.height > 25) target = b;
  }
  if (!target) target = page.getByRole('button', { name: /^Baixar$/ }).last();
  await target.click({ timeout: 15000 });
}

(async () => {
  const folderUrl = process.argv[2] || await ask('URL da pasta Canva: ');
  const limit = Number(process.argv[3] || '9999');
  const folderOverride = process.argv[4] || '';
  if (!folderUrl || !/^https?:\/\//.test(folderUrl)) {
    console.error('Uso: npm run download:safe -- "URL_DA_PASTA" 9999 "GEORGE"');
    process.exit(1);
  }

  const folderSlug = folderNameFromUrl(folderUrl, folderOverride);
  const targetDir = path.join(SAFE_DIR, folderSlug);
  fs.mkdirSync(targetDir, { recursive: true });
  const manifestPath = path.join(OUT_DIR, `download-safe-manifest_${folderSlug}.json`);
  const designsPath = path.join(OUT_DIR, `download-safe-designs_${folderSlug}.json`);
  let manifest = [];
  if (fs.existsSync(manifestPath)) {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  }
  const okById = new Map(manifest.filter(r => r.status === 'ok' && r.file && fs.existsSync(r.file)).map(r => [r.designId, r]));

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    acceptDownloads: true,
    viewport: { width: 1440, height: 950 },
    locale: 'pt-BR',
    args: ['--disable-blink-features=AutomationControlled']
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(folderUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(5000);

  console.log('Coletando designs por rolagem...');
  const designs = await collectAllByScrolling(page);
  fs.writeFileSync(designsPath, JSON.stringify(designs, null, 2));
  console.log(`Encontrados ${designs.length}. Pasta destino: ${targetDir}`);

  let processed = 0;
  for (const d of designs.slice(0, limit)) {
    processed++;
    if (okById.has(d.designId)) {
      console.log(`[SKIP ${processed}/${Math.min(limit, designs.length)}] ${d.name} (${d.designId})`);
      continue;
    }
    const rec = { name: d.name, designId: d.designId, status: 'started', format: '', file: '', error: '' };
    try {
      console.log(`\n[${processed}/${Math.min(limit, designs.length)}] ${d.name} (${d.designId})`);
      await findAndOpenMoreByDesignId(page, d.designId);
      await clickDownloadMenu(page);
      await page.waitForTimeout(1500);
      rec.format = await getSelectedFormat(page);
      console.log(`Formato Canva: ${rec.format}`);
      const downloadPromise = page.waitForEvent('download', { timeout: 240000 });
      await clickFinalDownload(page);
      const download = await downloadPromise;
      const suggested = download.suggestedFilename();
      const ext = path.extname(suggested) || (rec.format.toLowerCase().includes('mp4') ? '.mp4' : '.bin');
      const dest = uniqueDest(targetDir, d.name, d.designId, ext);
      await download.saveAs(dest);
      rec.file = dest;
      rec.status = 'ok';
      console.log(`OK: ${dest}`);
    } catch (e) {
      rec.status = 'error';
      rec.error = String(e && e.message || e).slice(0, 700);
      console.log(`ERRO: ${rec.error}`);
      await page.screenshot({ path: path.join(OUT_DIR, `error-safe-${safeName(d.name)}__${d.designId}.png`), fullPage: false }).catch(() => {});
    }
    const idx = manifest.findIndex(x => x.designId === rec.designId);
    if (idx >= 0) manifest[idx] = rec; else manifest.push(rec);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    await closeModal(page);
    await page.waitForTimeout(700);
  }
  const ok = manifest.filter(x => x.status === 'ok').length;
  const err = manifest.filter(x => x.status !== 'ok').length;
  console.log(`\nFinal: OK=${ok} ERRO=${err}`);
  console.log('Manifest:', manifestPath);
  console.log('Downloads:', targetDir);
  await ask('\nPressione ENTER para fechar o navegador... ');
  await context.close();
})();
