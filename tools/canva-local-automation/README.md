# MGS Canva Local Automation

Automação local assistida para testar acesso ao Canva no computador do Rodolfo, evitando bloqueio Cloudflare do VPS.

## O que este pacote faz agora

1. Abre um navegador Chromium local.
2. Permite login manual no Canva, incluindo código enviado por e-mail.
3. Salva a sessão localmente em `canva-profile/`.
4. Audita uma pasta Canva: screenshot, texto visível, HTML e elementos clicáveis.
5. Não baixa, não apaga e não move arquivos nesta primeira versão.

A ideia é primeiro validar que a automação local consegue abrir as pastas. Depois adaptamos o script aos botões reais da tela para separar imagem/vídeo e baixar no formato correto.

## Pré-requisito

Instalar Node.js LTS:

- Windows/Mac: https://nodejs.org/
- Depois abrir Terminal/PowerShell dentro desta pasta.

## Instalação

```bash
npm install
npm run setup
```

## 1) Testar login local

```bash
npm run login
```

O navegador vai abrir.

- Faça login no Canva manualmente.
- Se o Canva pedir código no e-mail, digite você mesmo.
- Quando estiver na tela de Projetos/Todos os projetos, volte ao terminal e pressione ENTER.

Arquivos gerados:

```text
output/login-check.json
output/login-check.png
```

## 2) Auditar uma pasta do Canva

Depois do login funcionar, rode:

```bash
npm run audit -- "COLE_AQUI_A_URL_DA_PASTA_CANVA"
```

Exemplo:

```bash
npm run audit -- "https://www.canva.com/folder/SEU_ID_AQUI"
```

O navegador vai abrir a pasta. Deixe a tela com os criativos visíveis e pressione ENTER no terminal.

Arquivos gerados em `output/`:

```text
*-audit.png
*-audit.json
*-audit.html
*-audit.txt
```

Envie para o Ares o `*-audit.json` e, se possível, o `*-audit.png`.

## Segurança

- Não coloque senha no Discord.
- Não envie código de login pelo Discord.
- A sessão fica salva apenas na pasta local `canva-profile/`.
- Para revogar, apague a pasta `canva-profile/` ou remova a sessão no Canva.

## Próxima fase

Após a auditoria de uma pasta real, o Ares adapta a automação para:

1. listar criativos por gestor;
2. identificar estático vs vídeo/animação;
3. baixar estáticos como PNG/JPG;
4. baixar vídeos/animações como MP4;
5. salvar em pastas separadas;
6. depois organizar para Drive.
