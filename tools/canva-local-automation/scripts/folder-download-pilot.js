const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
const DL_DIR = path.join(OUT_DIR, 'downloads');
fs.mkdirSync(DL_DIR, { recursive: true });

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
    .slice(0, 120) || 'canva';
}
async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
}
async function closeModalIfAny(page) {
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
  for (let i = 0; i < 80; i++) {
    for (const it of await collectVisible(page)) seen.set(it.designId, it);
    const before = seen.size;
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(700);
    for (const it of await collectVisible(page)) seen.set(it.designId, it);
    stable = seen.size === before ? stable + 1 : 0;
    if (stable >= 5) break;
  }
  await page.keyboard.press('Home').catch(() => {});
  await page.waitForTimeout(1000);
  return Array.from(seen.values());
}
async function openMoreForName(page, name) {
  const btn = page.getByRole('button', { name: new RegExp('Mais ações: ' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first();
  await btn.scrollIntoViewIfNeeded({ timeout: 10000 });
  await page.waitForTimeout(300);
  await btn.click({ timeout: 10000 });
}
async function clickDownloadMenu(page) {
  const item = page.getByText(/^Baixar$/).last();
  await item.click({ timeout: 10000 });
}
async function getSelectedFormat(page) {
  await page.getByRole('button', { name: /Formato de arquivo/i }).waitFor({ timeout: 15000 }).catch(() => {});
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
  await target.click({ timeout: 10000 });
}

(async () => {
  const folderUrl = process.argv[2] || await ask('URL da pasta Canva: ');
  const limit = Number(process.argv[3] || '3'); // piloto: 3 por padrão
  if (!folderUrl || !/^https?:\/\//.test(folderUrl)) {
    console.error('Uso: npm run download:pilot -- "URL_DA_PASTA" 3');
    process.exit(1);
  }
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
  fs.writeFileSync(path.join(OUT_DIR, 'download-pilot-designs.json'), JSON.stringify(designs, null, 2));
  console.log(`Encontrados ${designs.length} designs. Piloto vai baixar ${Math.min(limit, designs.length)}.`);

  const manifest = [];
  for (const d of designs.slice(0, limit)) {
    const rec = { name: d.name, designId: d.designId, status: 'started', format: '', file: '', error: '' };
    try {
      console.log(`\n[${manifest.length + 1}/${Math.min(limit, designs.length)}] ${d.name}`);
      await closeModalIfAny(page);
      await openMoreForName(page, d.name);
      await page.waitForTimeout(500);
      await clickDownloadMenu(page);
      await page.waitForTimeout(1500);
      rec.format = await getSelectedFormat(page);
      console.log(`Formato Canva: ${rec.format}`);
      const downloadPromise = page.waitForEvent('download', { timeout: 180000 });
      await clickFinalDownload(page);
      const download = await downloadPromise;
      const suggested = download.suggestedFilename();
      const ext = path.extname(suggested) || (rec.format.toLowerCase().includes('mp4') ? '.mp4' : '.bin');
      const filename = safeName(d.name) + ext;
      const dest = path.join(DL_DIR, filename);
      await download.saveAs(dest);
      rec.file = dest;
      rec.status = 'ok';
      console.log(`OK: ${dest}`);
    } catch (e) {
      rec.status = 'error';
      rec.error = String(e && e.message || e).slice(0, 500);
      console.log(`ERRO: ${rec.error}`);
      await page.screenshot({ path: path.join(OUT_DIR, `error-${safeName(d.name)}.png`), fullPage: false }).catch(() => {});
    }
    manifest.push(rec);
    fs.writeFileSync(path.join(OUT_DIR, 'download-pilot-manifest.json'), JSON.stringify(manifest, null, 2));
    await closeModalIfAny(page);
    await page.waitForTimeout(1000);
  }
  console.log('\nManifest:', path.join(OUT_DIR, 'download-pilot-manifest.json'));
  console.log('Downloads:', DL_DIR);
  await ask('\nPressione ENTER para fechar o navegador... ');
  await context.close();
})();
