const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
const DL_ROOT = path.join(OUT_DIR, 'downloads_V3');
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
function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}
function resolveInputPath(p) {
  if (!p) return '';
  return path.isAbsolute(p) ? p : path.join(ROOT, p);
}
function extFromFormat(format) {
  const f = String(format || '').toLowerCase();
  if (f.includes('mp4')) return '.mp4';
  if (f.includes('png')) return '.png';
  if (f.includes('jpg') || f.includes('jpeg')) return '.jpg';
  if (f.includes('gif')) return '.gif';
  return '.bin';
}
function uniqueDest(dir, name, designId, ext) {
  return path.join(dir, `${safeName(name)}__${designId}${ext}`);
}
function sameExtDestFromOldFile(dir, name, designId, oldFile, format) {
  const ext = path.extname(oldFile || '') || extFromFormat(format);
  return uniqueDest(dir, name, designId, ext);
}
async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 7000 }).catch(() => '');
}
async function closeMenus(page) {
  await page.keyboard.press('Escape').catch(() => {});
  await sleep(400);
}
async function scrollUntilDesignVisible(page, designId) {
  await closeMenus(page);
  await page.keyboard.press('Home').catch(() => {});
  await sleep(1000);

  for (let i = 0; i < 360; i++) {
    const row = await page.evaluate((id) => {
      const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
      if (!a) return null;
      const r = a.getBoundingClientRect();
      if (r.bottom > 115 && r.top < innerHeight - 20) {
        return { x: r.x, y: r.y, w: r.width, h: r.height };
      }
      return null;
    }, designId).catch(() => null);
    if (row) return row;
    await page.mouse.wheel(0, 300);
    await sleep(850);
  }
  throw new Error(`designId não encontrado/visível na rolagem: ${designId}`);
}
async function openMore(page, item) {
  const row = await scrollUntilDesignVisible(page, item.designId);

  const tries = [44, 70, 100];
  for (const offset of tries) {
    const x = Math.min(row.x + row.w - offset, 1365);
    const y = row.y + Math.min(row.h / 2, 40);
    await page.mouse.move(x, y);
    await sleep(300);
    await page.mouse.click(x, y);
    await sleep(900);

    const txt = await bodyText(page);
    if (/\bBaixar\b/.test(txt) && /Copiar link|Compartilhar|Mover|Detalhes|Fazer uma cópia|Abrir em uma nova aba/.test(txt)) return;
    await closeMenus(page);
  }

  const clicked = await page.evaluate((id) => {
    const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
    if (!a) return false;
    const ar = a.getBoundingClientRect();
    const btns = Array.from(document.querySelectorAll('button'));
    const candidates = btns.map(b => ({ b, r: b.getBoundingClientRect(), label: b.getAttribute('aria-label') || b.innerText || '' }))
      .filter(o => o.r.width > 20 && o.r.height > 20 && Math.abs((o.r.y + o.r.height / 2) - (ar.y + ar.height / 2)) < 35)
      .sort((a,b) => b.r.x - a.r.x);
    const more = candidates.find(o => /Mais ações|More actions/i.test(o.label)) || candidates[0];
    if (!more) return false;
    more.b.click();
    return true;
  }, item.designId).catch(() => false);

  if (!clicked) throw new Error(`não achei três pontinhos para ${item.name}`);
  await sleep(900);
  const txt = await bodyText(page);
  if (!/\bBaixar\b/.test(txt)) throw new Error(`menu abriu sem opção Baixar para ${item.name}`);
}
async function clickDownloadOption(page) {
  await page.getByText(/^Baixar$/).last().click({ timeout: 20000 });
}
async function getFormat(page) {
  await page.getByRole('button', { name: /Formato de arquivo/i }).waitFor({ timeout: 25000 }).catch(() => {});
  const txt = await bodyText(page);
  for (const f of ['Vídeo MP4', 'Video MP4', 'PNG', 'JPG', 'JPEG', 'GIF', 'PDF padrão', 'PDF para impressão']) {
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
    if (txt === 'Baixar' && box && box.width > 130 && box.height > 25) target = b;
  }
  if (!target) target = page.getByRole('button', { name: /^Baixar$/ }).last();
  await target.click({ timeout: 20000 });
}
function upsertManifest(manifest, rec) {
  const idx = manifest.findIndex(x => x.designId === rec.designId);
  if (idx >= 0) manifest[idx] = rec; else manifest.push(rec);
}

(async () => {
  const folderUrl = process.argv[2] || await ask('URL da pasta Canva: ');
  const folderName = safeName(process.argv[3] || 'PASTA');
  const sourceManifestArg = process.argv[4] || '';
  const mode = (process.argv[5] || 'all').toLowerCase(); // all | errors

  if (!folderUrl || !/^https?:\/\//.test(folderUrl) || !sourceManifestArg) {
    console.error('Uso: npm run download:from-manifest -- "URL_DA_PASTA" "GEORGE" "output/download-pilot-manifest_GEORGE.json"');
    console.error('Retry só erros: npm run download:from-manifest -- "URL_DA_PASTA" "GEORGE" "output/download-pilot-manifest_GEORGE.json" errors');
    process.exit(1);
  }

  const sourceManifestPath = resolveInputPath(sourceManifestArg);
  const source = readJson(sourceManifestPath, null);
  if (!Array.isArray(source) || source.length === 0) {
    console.error(`Manifest fonte inválido ou vazio: ${sourceManifestPath}`);
    process.exit(1);
  }

  const items = [];
  const seen = new Set();
  for (const r of source) {
    if (!r || !r.designId || seen.has(r.designId)) continue;
    seen.add(r.designId);
    items.push({ name: r.name || 'Design sem nome', designId: r.designId });
  }

  const targetDir = path.join(DL_ROOT, folderName);
  fs.mkdirSync(targetDir, { recursive: true });
  const manifestPath = path.join(OUT_DIR, `download-v3-manifest_${folderName}.json`);
  let manifest = readJson(manifestPath, []);

  // Importa/copía OKs do V2, se existir, para não rebaixar o que já foi concluído.
  const v2ManifestPath = path.join(OUT_DIR, `download-v2-manifest_${folderName}.json`);
  const v2 = readJson(v2ManifestPath, []);
  if (Array.isArray(v2) && v2.length) {
    for (const r of v2) {
      if (r.status !== 'ok' || !r.file || !fs.existsSync(r.file)) continue;
      const dest = sameExtDestFromOldFile(targetDir, r.name, r.designId, r.file, r.format);
      if (!fs.existsSync(dest)) fs.copyFileSync(r.file, dest);
      upsertManifest(manifest, { name: r.name, designId: r.designId, status: 'ok', format: r.format || '', file: dest, error: '', source: 'copied_from_v2' });
    }
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  }

  const okMap = () => new Map(manifest.filter(r => r.status === 'ok' && r.file && fs.existsSync(r.file)).map(r => [r.designId, r]));
  const previousErrors = new Set(manifest.filter(r => r.status !== 'ok').map(r => r.designId));
  let queue = items;
  if (mode === 'errors') queue = items.filter(x => previousErrors.has(x.designId) || !okMap().has(x.designId));

  console.log(`Fonte: ${sourceManifestPath}`);
  console.log(`Itens na lista-mestre: ${items.length}`);
  console.log(`Destino: ${targetDir}`);
  console.log(`Manifest V3: ${manifestPath}`);
  console.log(`Modo: ${mode}`);

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

  let n = 0;
  for (const item of queue) {
    n++;
    if (okMap().has(item.designId)) {
      console.log(`[SKIP ${n}/${queue.length}] ${item.name} (${item.designId})`);
      continue;
    }

    const rec = { name: item.name, designId: item.designId, status: 'started', format: '', file: '', error: '', source: 'downloaded_v3' };
    try {
      console.log(`\n[${n}/${queue.length}] ${item.name} (${item.designId})`);
      await openMore(page, item);
      await clickDownloadOption(page);
      await sleep(1600);
      rec.format = await getFormat(page);
      console.log(`Formato Canva: ${rec.format}`);

      const downloadPromise = page.waitForEvent('download', { timeout: 240000 });
      await clickFinalDownload(page);
      const download = await downloadPromise;
      const suggested = download.suggestedFilename();
      const ext = path.extname(suggested) || extFromFormat(rec.format);
      const dest = uniqueDest(targetDir, item.name, item.designId, ext);
      await download.saveAs(dest);

      rec.status = 'ok';
      rec.file = dest;
      console.log(`OK: ${dest}`);
    } catch (e) {
      rec.status = 'error';
      rec.error = String(e && e.message || e).slice(0, 900);
      console.log(`ERRO: ${rec.error}`);
      await page.screenshot({ path: path.join(OUT_DIR, `error-v3-${safeName(item.name)}__${item.designId}.png`), fullPage: false }).catch(() => {});
    }

    upsertManifest(manifest, rec);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    await closeMenus(page);
    await sleep(1000);
  }

  const ok = manifest.filter(x => x.status === 'ok' && x.file && fs.existsSync(x.file)).length;
  const err = manifest.filter(x => x.status !== 'ok').length;
  console.log(`\nFinal: OK=${ok} ERRO=${err} TOTAL_MANIFEST=${manifest.length}`);
  console.log('Manifest:', manifestPath);
  console.log('Downloads:', targetDir);
  await ask('\nPressione ENTER para fechar o navegador... ');
  await context.close();
})();
