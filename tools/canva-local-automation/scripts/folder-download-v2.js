const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
const DL_ROOT = path.join(OUT_DIR, 'downloads_V2');
fs.mkdirSync(DL_ROOT, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));
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
    .slice(0, 90) || 'canva';
}
function uniquePath(dir, name, designId, ext) {
  return path.join(dir, `${safeName(name)}__${designId}${ext}`);
}
async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 7000 }).catch(() => '');
}
async function closeMenus(page) {
  await page.keyboard.press('Escape').catch(() => {});
  await sleep(350);
}
async function collectVisible(page) {
  return await page.evaluate(() => {
    const out = [];
    const anchors = Array.from(document.querySelectorAll('a[href*="/design/editor/shell"]'));
    for (const a of anchors) {
      const r = a.getBoundingClientRect();
      const href = a.href || '';
      const m = href.match(/designId=([^&]+)/);
      const name = (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
      if (!m || !name) continue;
      out.push({
        name,
        href,
        designId: m[1],
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
        visible: r.bottom > 120 && r.top < innerHeight - 20
      });
    }
    return out;
  });
}
async function collectAllSlow(page) {
  const seen = new Map();
  let stable = 0;
  await page.keyboard.press('Home').catch(() => {});
  await sleep(1200);

  for (let i = 0; i < 260; i++) {
    for (const d of await collectVisible(page)) seen.set(d.designId, d);
    const before = seen.size;

    // rolagem menor e pausa maior para Canva virtualizar com calma
    await page.mouse.wheel(0, 320);
    await sleep(1200);

    for (const d of await collectVisible(page)) seen.set(d.designId, d);
    stable = seen.size === before ? stable + 1 : 0;
    console.log(`Coleta: ${seen.size} designs encontrados...`);
    if (stable >= 10) break;
  }

  await page.keyboard.press('Home').catch(() => {});
  await sleep(1500);
  return Array.from(seen.values());
}
async function scrollUntilDesignVisible(page, designId) {
  await closeMenus(page);
  await page.keyboard.press('Home').catch(() => {});
  await sleep(900);

  for (let i = 0; i < 300; i++) {
    const row = await page.evaluate((id) => {
      const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
      if (!a) return null;
      const r = a.getBoundingClientRect();
      if (r.bottom > 120 && r.top < innerHeight - 20) return { x: r.x, y: r.y, w: r.width, h: r.height };
      return null;
    }, designId).catch(() => null);
    if (row) return row;
    await page.mouse.wheel(0, 320);
    await sleep(700);
  }
  throw new Error(`designId não ficou visível após rolagem lenta: ${designId}`);
}
async function openMore(page, design) {
  const row = await scrollUntilDesignVisible(page, design.designId);

  // Clica na área dos três pontos no fim da linha/card.
  const x = Math.min(row.x + row.w - 44, 1365);
  const y = row.y + Math.min(row.h / 2, 40);
  await page.mouse.move(x, y);
  await sleep(250);
  await page.mouse.click(x, y);
  await sleep(800);

  let txt = await bodyText(page);
  if (/\bBaixar\b/.test(txt) && /Copiar link|Compartilhar|Mover|Detalhes|Fazer uma cópia|Abrir em uma nova aba/.test(txt)) return;

  // fallback: botão na mesma linha
  const clicked = await page.evaluate((id) => {
    const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
    if (!a) return false;
    const ar = a.getBoundingClientRect();
    const btns = Array.from(document.querySelectorAll('button'));
    const candidates = btns.map(b => ({ b, r: b.getBoundingClientRect(), label: b.getAttribute('aria-label') || b.innerText || '' }))
      .filter(o => o.r.width > 20 && o.r.height > 20 && Math.abs((o.r.y + o.r.height / 2) - (ar.y + ar.height / 2)) < 28)
      .sort((a,b) => b.r.x - a.r.x);
    const more = candidates.find(o => /Mais ações|More actions/i.test(o.label)) || candidates[0];
    if (!more) return false;
    more.b.click();
    return true;
  }, design.designId).catch(() => false);
  if (!clicked) throw new Error(`não achei três pontinhos para ${design.name}`);

  await sleep(800);
  txt = await bodyText(page);
  if (!/\bBaixar\b/.test(txt)) throw new Error(`menu abriu sem Baixar para ${design.name}`);
}
async function clickDownloadOption(page) {
  await page.getByText(/^Baixar$/).last().click({ timeout: 15000 });
}
async function getFormat(page) {
  await page.getByRole('button', { name: /Formato de arquivo/i }).waitFor({ timeout: 20000 }).catch(() => {});
  const txt = await bodyText(page);
  for (const f of ['Vídeo MP4', 'Video MP4', 'PNG', 'JPG', 'GIF', 'PDF padrão', 'PDF para impressão']) {
    if (txt.includes(f)) return f;
  }
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
  const folderName = safeName(process.argv[3] || 'PASTA');
  const mode = (process.argv[4] || 'all').toLowerCase(); // all | errors

  if (!folderUrl || !/^https?:\/\//.test(folderUrl)) {
    console.error('Uso: npm run download:v2 -- "URL_DA_PASTA" "GEORGE"');
    console.error('Retry só erros: npm run download:v2 -- "URL_DA_PASTA" "GEORGE" errors');
    process.exit(1);
  }

  const targetDir = path.join(DL_ROOT, folderName);
  fs.mkdirSync(targetDir, { recursive: true });
  const manifestPath = path.join(OUT_DIR, `download-v2-manifest_${folderName}.json`);
  const designsPath = path.join(OUT_DIR, `download-v2-designs_${folderName}.json`);

  let manifest = [];
  if (fs.existsSync(manifestPath)) manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    acceptDownloads: true,
    viewport: { width: 1440, height: 950 },
    locale: 'pt-BR',
    args: ['--disable-blink-features=AutomationControlled']
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(folderUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);

  console.log('Coletando designs com rolagem lenta...');
  const designs = await collectAllSlow(page);
  fs.writeFileSync(designsPath, JSON.stringify(designs, null, 2));
  console.log(`Coletados ${designs.length} designs. Destino: ${targetDir}`);

  const okExisting = new Map(manifest.filter(r => r.status === 'ok' && r.file && fs.existsSync(r.file)).map(r => [r.designId, r]));
  const errExisting = new Set(manifest.filter(r => r.status !== 'ok').map(r => r.designId));

  let queue = designs;
  if (mode === 'errors') queue = designs.filter(d => errExisting.has(d.designId) || !okExisting.has(d.designId));

  let n = 0;
  for (const d of queue) {
    n++;
    if (okExisting.has(d.designId)) {
      console.log(`[SKIP ${n}/${queue.length}] ${d.name} (${d.designId})`);
      continue;
    }

    const rec = { name: d.name, designId: d.designId, status: 'started', format: '', file: '', error: '' };
    try {
      console.log(`\n[${n}/${queue.length}] ${d.name} (${d.designId})`);
      await openMore(page, d);
      await clickDownloadOption(page);
      await sleep(1500);
      rec.format = await getFormat(page);
      console.log(`Formato Canva: ${rec.format}`);

      const downloadPromise = page.waitForEvent('download', { timeout: 240000 });
      await clickFinalDownload(page);
      const download = await downloadPromise;
      const suggested = download.suggestedFilename();
      const ext = path.extname(suggested) || (rec.format.toLowerCase().includes('mp4') ? '.mp4' : '.bin');
      const dest = uniquePath(targetDir, d.name, d.designId, ext);
      await download.saveAs(dest);

      rec.status = 'ok';
      rec.file = dest;
      console.log(`OK: ${dest}`);
    } catch (e) {
      rec.status = 'error';
      rec.error = String(e && e.message || e).slice(0, 700);
      console.log(`ERRO: ${rec.error}`);
      await page.screenshot({ path: path.join(OUT_DIR, `error-v2-${safeName(d.name)}__${d.designId}.png`), fullPage: false }).catch(() => {});
    }

    const idx = manifest.findIndex(x => x.designId === rec.designId);
    if (idx >= 0) manifest[idx] = rec; else manifest.push(rec);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    await closeMenus(page);
    await sleep(1000);
  }

  const ok = manifest.filter(x => x.status === 'ok').length;
  const err = manifest.filter(x => x.status !== 'ok').length;
  console.log(`\nFinal: OK=${ok} ERRO=${err}`);
  console.log('Manifest:', manifestPath);
  console.log('Downloads:', targetDir);
  await ask('\nPressione ENTER para fechar o navegador... ');
  await context.close();
})();
