# Canva NICOLAS V3 — recuperação via Chrome CDP e manifest limpo

Use quando uma pasta Canva grande já tem downloads parciais locais, mas os manifests V2 estão incorretos/incompletos e o Playwright abre em loop de Cloudflare.

## Situação observada

- Pasta `CRIATIVOS - NICOLAS` mostrava 334 itens no Canva.
- Downloads locais tinham 59 arquivos válidos em `output/downloads_V2/NICOLAS` e/ou `output/downloads_V2/999`.
- Manifests disponíveis eram ruins para fonte final:
  - `download-v2-manifest_NICOLAS.json`: só 3 erros de execução abortada.
  - `download-v2-manifest_999.json`: 60 itens, 59 OK + 1 erro, mas não representa os 334 da pasta.
- Rodar Playwright com perfil novo (`.playwright-canva-profile`) caía no Cloudflare/Canva `Just a moment...` em loop.

## Padrão recomendado

1. Não tratar manifest parcial como final.
2. Criar V3 separado: `output/downloads_V3/NICOLAS/`.
3. Seed dos já baixados deve vir dos arquivos reais no disco, não de lista colada no chat.
4. Deduplicar por `designId` extraído do sufixo `__designId.ext`.
5. Conectar o script ao Chrome normal já aberto via CDP, em vez de lançar novo Chromium Playwright.
6. Coletar lista-mestre da pasta Canva; validar antes de qualquer download.
7. Só baixar pendentes quando os números fecharem:

```text
Campo                 | Esperado
----------------------|---------
Itens Canva            | 334
Seed IDs únicos        | 59
Master limpo           | 334
Pendentes              | 275
```

## Chrome normal com remote debugging

Quando Cloudflare bloquear o Chromium do Playwright, abra o Chrome real do Windows com CDP:

```powershell
cd C:\Users\matte\canva-ares\canva-local-automation

$chrome="$Env:ProgramFiles\Google\Chrome\Application\chrome.exe"
if (!(Test-Path $chrome)) {
  $chrome="${Env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}

& $chrome --remote-debugging-port=9222 --user-data-dir="C:\Users\matte\canva-ares\canva-local-automation\canva-profile-cdp" "https://www.canva.com/folder/FAFSo0VURMk"
```

Rodolfo passa Cloudflare/login manualmente nessa janela. Deixar a pasta aberta.

No script Node, conectar assim:

```js
const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
const context = browser.contexts()[0];
let page =
  context.pages().find((p) => p.url().includes('canva.com/folder')) ||
  context.pages().find((p) => p.url().includes('canva.com')) ||
  context.pages()[0];
if (!page) page = await context.newPage();
await page.goto(FOLDER_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
```

Não fechar o contexto no final; ele é o Chrome real do usuário.

## Pitfall: coletar IDs demais

Regex pesada em `document.documentElement.innerHTML` pode capturar IDs extras de thumbnails/cache/preview. Exemplo: coletor retornou `342/334` e pendentes `283` quando o correto era `334/334` e `275`.

Quando isso acontecer:

1. Não baixar.
2. Diagnosticar quantos IDs têm `name` ou `url` de item real visível.
3. Se `com_nome_ou_url=334` e `sem_nome_e_sem_url=8`, filtrar os 8 sem evidência de linha visível.
4. Gerar `download-v3-master_NICOLAS_334_clean.json` e `download-v3-pending_NICOLAS_clean.json`.
5. Só prosseguir se o clean mostrar `Master limpo: 334` e `Pendentes: 275`.

Comando diagnóstico em PowerShell:

```powershell
cd C:\Users\matte\canva-ares\canva-local-automation
node -e "const fs=require('fs'); const m=JSON.parse(fs.readFileSync('output/download-v3-master_NICOLAS_334.json','utf8')); const stats={total:m.length, com_nome:m.filter(x=>x.name&&x.name.trim()).length, com_url:m.filter(x=>x.url&&x.url.trim()).length, com_nome_ou_url:m.filter(x=>(x.name&&x.name.trim())||(x.url&&x.url.trim())).length, sem_nome_e_sem_url:m.filter(x=>!(x.name&&x.name.trim())&&!(x.url&&x.url.trim())).length}; console.table(stats); console.log('Sem nome/url:'); console.log(m.filter(x=>!(x.name&&x.name.trim())&&!(x.url&&x.url.trim())).map(x=>x.designId).join('\n'));"
```

Filtro quando a condição 334/8 for confirmada:

```powershell
node -e "const fs=require('fs'); const masterPath='output/download-v3-master_NICOLAS_334.json'; const seedPath='output/download-v3-seed_NICOLAS_existing.json'; const m=JSON.parse(fs.readFileSync(masterPath,'utf8')); const seed=JSON.parse(fs.readFileSync(seedPath,'utf8')); const clean=m.filter(x=>(x.name&&x.name.trim())||(x.url&&x.url.trim())).slice(0,334); const seedIds=new Set(seed.filter(x=>x.status==='ok'&&x.designId).map(x=>x.designId)); const pending=clean.filter(x=>!seedIds.has(x.designId)).map(x=>({name:x.name||'',designId:x.designId,status:'pending',format:'',file:'',error:'',source_url:x.url||''})); fs.copyFileSync(masterPath,'output/download-v3-master_NICOLAS_342_backup.json'); fs.writeFileSync('output/download-v3-master_NICOLAS_334_clean.json',JSON.stringify(clean,null,2)); fs.writeFileSync('output/download-v3-pending_NICOLAS_clean.json',JSON.stringify(pending,null,2)); console.log('Master limpo:',clean.length); console.log('Pendentes:',pending.length);"
```

## Comunicação com Rodolfo em scripts longos

- Se anexo via Discord não chegar, não insistir em `MEDIA:`; enviar código inline.
- Para código grande, primeiro dizer exatamente o caminho do arquivo e se é substituição total ou patch.
- Dividir em blocos pequenos quando Discord cortar mensagem.
- Em Windows/PowerShell, sempre lembrar de rodar da raiz do projeto (`C:\Users\matte\canva-ares\canva-local-automation`), não de subpastas como `output\downloads_V2\NICOLAS`.
