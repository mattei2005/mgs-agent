const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const PROFILE_DIR = path.join(ROOT, 'canva-profile');
const OUT_DIR = path.join(ROOT, 'output');
fs.mkdirSync(OUT_DIR, { recursive: true });

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => rl.question(question, answer => { rl.close(); resolve(answer); }));
}

function slug(s) {
  return (s || 'canva-design')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 90) || 'canva-design';
}

(async () => {
  const designUrl = process.argv[2] || await ask('Cole a URL de UM design do Canva para auditar exportação: ');
  if (!designUrl || !/^https?:\/\//.test(designUrl)) {
    console.error('URL inválida. Exemplo: npm run design:audit -- https://www.canva.com/design/editor/shell?...');
    process.exit(1);
  }

  console.log('\nAbrindo design no Canva local...');
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    acceptDownloads: true,
    viewport: { width: 1440, height: 950 },
    locale: 'pt-BR',
    args: ['--disable-blink-features=AutomationControlled']
  });

  const page = context.pages()[0] || await context.newPage();
  await page.goto(designUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(10000);

  console.log('\nIMPORTANTE: não clique no botão final de download ainda.');
  console.log('No navegador, abra o painel de download/exportação do Canva.');
  console.log('Normalmente: Compartilhar > Baixar, ou Arquivo > Baixar.');
  console.log('Deixe visível a lista/opção de formatos: PNG, JPG, Vídeo MP4, GIF etc.');
  await ask('Quando o painel de download estiver aberto, pressione ENTER aqui... ');

  await page.waitForTimeout(1500);
  const title = await page.title().catch(() => 'canva-design');
  const bodyText = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  const base = slug(title.replace(/ - Canva.*/i, '') || 'canva-design');
  const shot = path.join(OUT_DIR, `${base}-export-audit.png`);
  const txtPath = path.join(OUT_DIR, `${base}-export-audit.txt`);
  const jsonPath = path.join(OUT_DIR, `${base}-export-audit.json`);

  await page.screenshot({ path: shot, fullPage: false }).catch(() => {});
  fs.writeFileSync(txtPath, bodyText);

  const elements = await page.evaluate(() => {
    const pick = [];
    const nodes = Array.from(document.querySelectorAll('a, button, input, [role="button"], [aria-label]'));
    for (const el of nodes.slice(0, 800)) {
      const rect = el.getBoundingClientRect();
      const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ');
      if (!text && !el.getAttribute('href')) continue;
      if (rect.width < 2 || rect.height < 2) continue;
      pick.push({
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        text: text.slice(0, 200),
        href: el.getAttribute('href') || '',
        aria: el.getAttribute('aria-label') || '',
        x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)
      });
    }
    return pick;
  }).catch(() => []);

  const hasMp4 = /Vídeo\s*MP4|Video\s*MP4|MP4/i.test(bodyText);
  const hasGif = /GIF/i.test(bodyText);
  const hasPng = /\bPNG\b/i.test(bodyText);
  const hasJpg = /\bJPG\b|\bJPEG\b/i.test(bodyText);
  const hasStaticOnly = (hasPng || hasJpg) && !hasMp4 && !hasGif;
  const likelyKind = hasMp4 ? 'VIDEO_OR_ANIMATED_EXPORT_AVAILABLE' : hasStaticOnly ? 'STATIC_IMAGE_ONLY_VISIBLE' : 'UNKNOWN_NEEDS_REVIEW';

  const report = {
    ok: true,
    stage: 'design_export_audit_only_no_download',
    url: page.url(),
    title,
    likely_kind: likelyKind,
    detected_formats: { png: hasPng, jpg: hasJpg, mp4: hasMp4, gif: hasGif },
    screenshot: shot,
    text_file: txtPath,
    elements_count: elements.length,
    elements: elements.slice(0, 300),
    checked_at: new Date().toISOString()
  };
  fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));

  console.log('\nAuditoria de exportação salva em output/:');
  console.log(`- ${path.relative(ROOT, shot)}`);
  console.log(`- ${path.relative(ROOT, jsonPath)}`);
  console.log('\nClassificação preliminar:', likelyKind);
  console.log('Formatos detectados:', JSON.stringify(report.detected_formats));
  console.log('\nEnvie o JSON e o PNG para o Ares.');

  await ask('\nPressione ENTER para encerrar o navegador... ');
  await context.close();
})();
