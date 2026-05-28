const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
const SAFE_DIR = path.join(OUT_DIR, 'downloads_VISIBLE');
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
async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
}
async function closeModal(page) {
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(500);
}
async function visibleDesigns(page) {
  return await page.evaluate(() => {
    const out = [];
    const anchors = Array.from(document.querySelectorAll('a[href*="/design/editor/shell"]'));
    for (const a of anchors) {
      const r = a.getBoundingClientRect();
      const name = (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
      const href = a.href;
      const m = href.match(/designId=([^&]+)/);
      if (!name || !m) continue;
      if (r.bottom < 120 || r.top > innerHeight - 20) continue;
      out.push({ name, href, designId: m[1], x: r.x, y: r.y, w: r.width, h: r.height });
    }
    return out.sort((a,b) => a.y - b.y);
  });
}
async function openMoreForVisibleDesign(page, d) {
  await closeModal(page);
  const row = await page.evaluate((id) => {
    const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
    if (!a) return null;
    const r = a.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  }, d.designId);
  if (!row) throw new Error(`Item não está visível: ${d.designId}`);

  const x = Math.min(row.x + row.w - 44, 1360);
  const y = row.y + Math.min(row.h / 2, 40);
  await page.mouse.move(x, y);
  await page.waitForTimeout(250);
  await page.mouse.click(x, y);
  await page.waitForTimeout(700);

  let txt = await bodyText(page);
  if (/\bBaixar\b/.test(txt) && /Copiar link|Compartilhar|Mover|Detalhes|Fazer uma cópia/.test(txt)) return;

  const clicked = await page.evaluate((id) => {
    const a = document.querySelector(`a[href*="designId=${CSS.escape(id)}"]`);
    if (!a) return false;
    const ar = a.getBoundingClientRect();
    const btns = Array.from(document.querySelectorAll('button'));
    const candidates = btns.map(b => ({ b, r: b.getBoundingClientRect(), label: b.getAttribute('aria-label') || b.innerText || '' }))
      .filter(o => o.r.width > 20 && o.r.height > 20 && Math.abs((o.r.y + o.r.height / 2) - (ar.y + ar.height / 2)) < 26)
      .sort((a, b) => b.r.x - a.r.x);
    const more = candidates.find(o => /Mais ações|More actions|\.\.\./i.test(o.label)) || candidates[0];
    if (more) { more.b.click(); return true; }
    return false;
  }, d.designId).catch(() => false);
  if (!clicked) throw new Error(`Não achei Mais ações visível para ${d.name}`);
  await page.waitForTimeout(700);
  txt = await bodyText(page);
  if (!/\bBaixar\b/.test(txt)) throw new Error(`Menu abriu, mas não achei opção Baixar para ${d.name}`);
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
function saveManifest(pathName, manifest) {
  fs.writeFileSync(pathName, JSON.stringify(manifest, null, 2));
}

(async () => {
  const folderUrl = process.argv[2] || await ask('URL da pasta Canva: ');
  const folderName = safeName(process.argv[3] || 'PASTA');
  if (!folderUrl || !/^https?:\/\//.test(folderUrl)) {
    console.error('Uso: npm run download:visible -- "URL_DA_PASTA" "GEORGE"');
    process.exit(1);
  }

  const targetDir = path.join(SAFE_DIR, folderName);
  fs.mkdirSync(targetDir, { recursive: true });
  const manifestPath = path.join(OUT_DIR, `download-visible-manifest_${folderName}.json`);
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
  await page.waitForTimeout(5000);

  console.log('\nModo assistido por tela visível.');
  console.log('1) Role manualmente a pasta no Canva.');
  console.log('2) Deixe um bloco de itens visível.');
  console.log('3) Pressione ENTER aqui para baixar só os visíveis.');
  console.log('4) Digite q + ENTER para sair.');
  console.log(`Destino: ${targetDir}\n`);

  while (true) {
    const ans = (await ask('\nENTER = baixar visíveis | q = sair: ')).trim().toLowerCase();
    if (ans === 'q' || ans === 'quit' || ans === 'sair') break;

    const visible = await visibleDesigns(page);
    console.log(`Visíveis detectados: ${visible.length}`);
    let okById = new Map(manifest.filter(r => r.status === 'ok' && r.file && fs.existsSync(r.file)).map(r => [r.designId, r]));
    let batchOk = 0, batchSkip = 0, batchErr = 0;

    for (const d of visible) {
      if (okById.has(d.designId)) {
        batchSkip++;
        console.log(`[SKIP] ${d.name} (${d.designId})`);
        continue;
      }
      const rec = { name: d.name, designId: d.designId, status: 'started', format: '', file: '', error: '' };
      try {
        console.log(`\n[BAIXANDO] ${d.name} (${d.designId})`);
        await openMoreForVisibleDesign(page, d);
        await clickDownloadMenu(page);
        await page.waitForTimeout(1400);
        rec.format = await getSelectedFormat(page);
        console.log(`Formato Canva: ${rec.format}`);
        const downloadPromise = page.waitForEvent('download', { timeout: 240000 });
        await clickFinalDownload(page);
        const download = await downloadPromise;
        const suggested = download.suggestedFilename();
        const ext = path.extname(suggested) || (rec.format.toLowerCase().includes('mp4') ? '.mp4' : '.bin');
        const dest = path.join(targetDir, `${safeName(d.name)}__${d.designId}${ext}`);
        await download.saveAs(dest);
        rec.status = 'ok';
        rec.file = dest;
        batchOk++;
        console.log(`OK: ${dest}`);
      } catch (e) {
        rec.status = 'error';
        rec.error = String(e && e.message || e).slice(0, 700);
        batchErr++;
        console.log(`ERRO: ${rec.error}`);
        await page.screenshot({ path: path.join(OUT_DIR, `error-visible-${safeName(d.name)}__${d.designId}.png`), fullPage: false }).catch(() => {});
      }
      const idx = manifest.findIndex(x => x.designId === rec.designId);
      if (idx >= 0) manifest[idx] = rec; else manifest.push(rec);
      saveManifest(manifestPath, manifest);
      await closeModal(page);
      await page.waitForTimeout(700);
    }
    const totalOk = manifest.filter(x => x.status === 'ok').length;
    const totalErr = manifest.filter(x => x.status !== 'ok').length;
    console.log(`\nLote: OK=${batchOk} SKIP=${batchSkip} ERRO=${batchErr}`);
    console.log(`Total manifest: OK=${totalOk} ERRO=${totalErr}`);
    console.log(`Manifest: ${manifestPath}`);
  }

  console.log('Encerrando.');
  await context.close();
})();
