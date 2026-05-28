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
  return (s || 'canva-folder')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'canva-folder';
}

(async () => {
  const folderUrl = process.argv[2] || await ask('Cole a URL da pasta do Canva para auditar: ');
  if (!folderUrl || !/^https?:\/\//.test(folderUrl)) {
    console.error('URL inválida. Exemplo: npm run audit -- https://www.canva.com/folder/...');
    process.exit(1);
  }

  console.log('\nAbrindo pasta no navegador local com a sessão salva...');
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    acceptDownloads: true,
    viewport: { width: 1440, height: 950 },
    locale: 'pt-BR',
    args: ['--disable-blink-features=AutomationControlled']
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(folderUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);

  console.log('\nSe a pasta não carregou, faça login/autorize no navegador.');
  console.log('Depois deixe a tela da pasta aberta com os criativos visíveis.');
  await ask('Pressione ENTER para capturar auditoria da tela atual... ');

  await page.waitForTimeout(1000);
  const title = await page.title().catch(() => 'canva-folder');
  const bodyText = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  const name = slug(title || 'canva-folder');
  const shot = path.join(OUT_DIR, `${name}-audit.png`);
  const htmlPath = path.join(OUT_DIR, `${name}-audit.html`);
  const txtPath = path.join(OUT_DIR, `${name}-audit.txt`);
  const jsonPath = path.join(OUT_DIR, `${name}-audit.json`);

  await page.screenshot({ path: shot, fullPage: true }).catch(async () => {
    await page.screenshot({ path: shot, fullPage: false }).catch(() => {});
  });
  fs.writeFileSync(htmlPath, await page.content().catch(() => ''));
  fs.writeFileSync(txtPath, bodyText);

  // Coleta leve de elementos clicáveis visíveis. Não baixa nada ainda.
  const elements = await page.evaluate(() => {
    const pick = [];
    const nodes = Array.from(document.querySelectorAll('a, button, [role="button"], [aria-label]'));
    for (const el of nodes.slice(0, 500)) {
      const rect = el.getBoundingClientRect();
      const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().replace(/\s+/g, ' ');
      if (!text && !el.getAttribute('href')) continue;
      if (rect.width < 2 || rect.height < 2) continue;
      pick.push({
        tag: el.tagName,
        text: text.slice(0, 160),
        href: el.getAttribute('href') || '',
        aria: el.getAttribute('aria-label') || '',
        x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)
      });
    }
    return pick;
  }).catch(() => []);

  const report = {
    ok: true,
    stage: 'folder_audit_only_no_download',
    url: page.url(),
    title,
    screenshot: shot,
    html: htmlPath,
    text_file: txtPath,
    elements_count: elements.length,
    elements: elements.slice(0, 200),
    checked_at: new Date().toISOString()
  };
  fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));

  console.log('\nAuditoria salva em output/:');
  console.log(`- ${path.relative(ROOT, shot)}`);
  console.log(`- ${path.relative(ROOT, jsonPath)}`);
  console.log('\nEnvie o JSON/screenshot de volta para o Ares se a página carregou.');
  console.log('A próxima versão será adaptada aos botões reais da sua tela para baixar IMG/VID separado.');

  await ask('\nPressione ENTER para encerrar o navegador... ');
  await context.close();
})();
