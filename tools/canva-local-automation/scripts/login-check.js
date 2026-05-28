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

(async () => {
  console.log('\n[MGS Canva Local Automation]');
  console.log('Abrindo navegador local. Faça login no Canva normalmente.');
  console.log('Nenhuma senha/código é enviado ao Ares. Tudo fica neste computador.\n');

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    acceptDownloads: true,
    viewport: { width: 1440, height: 950 },
    locale: 'pt-BR',
    args: ['--disable-blink-features=AutomationControlled']
  });

  const page = context.pages()[0] || await context.newPage();
  await page.goto('https://www.canva.com/', { waitUntil: 'domcontentloaded', timeout: 90000 });

  console.log('1) Se pedir login, faça login com o usuário Canva MGS.');
  console.log('2) Se pedir código no e-mail, digite você mesmo no navegador.');
  console.log('3) Quando estiver vendo Projetos/Todos os projetos, volte aqui.\n');
  await ask('Pressione ENTER aqui depois que o Canva estiver logado... ');

  await page.waitForTimeout(2000);
  const text = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  const shot = path.join(OUT_DIR, 'login-check.png');
  await page.screenshot({ path: shot, fullPage: false }).catch(() => {});

  const logged = /Projetos|Todos os projetos|Criar um design|Início|Home/i.test(text) && !/Concluir login|Inserir código/i.test(text);
  const report = {
    ok: logged,
    url: page.url(),
    screenshot: shot,
    detected_text: text.replace(/\s+/g, ' ').slice(0, 500),
    checked_at: new Date().toISOString()
  };
  fs.writeFileSync(path.join(OUT_DIR, 'login-check.json'), JSON.stringify(report, null, 2));

  if (logged) {
    console.log('\nOK: sessão Canva local parece logada.');
    console.log('Arquivo gerado: output/login-check.json');
  } else {
    console.log('\nATENÇÃO: não consegui confirmar login automaticamente.');
    console.log('Verifique output/login-check.png e output/login-check.json');
  }

  console.log('\nPode fechar o navegador quando quiser. A sessão fica salva em canva-profile/.');
  await ask('Pressione ENTER para encerrar o navegador... ');
  await context.close();
})();
