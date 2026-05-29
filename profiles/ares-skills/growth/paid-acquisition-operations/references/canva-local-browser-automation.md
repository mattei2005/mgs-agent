# Canva local browser automation fallback — MGS criativos

Use quando a Canva Connect API não for viável para uso interno (ex.: plano Canva Teams sem private integration Enterprise) e Rodolfo quiser automatizar downloads de pastas do Canva pelo computador local.

## Contexto operacional

- Kelly coloca criativos em pastas por gestor, misturando imagem, vídeo/animação, feed, stories e idiomas.
- O Canva em lote exige escolher um único formato para todos; isso quebra quando há imagem e vídeo misturados.
- O VPS/navegador remoto pode ser bloqueado por Cloudflare/anti-bot do Canva; a alternativa viável é Playwright rodando no Windows do Rodolfo, usando navegador local já logado.
- Não pedir senha/código no chat. O login/código de e-mail deve ser digitado pelo usuário no navegador local.

## Regra crítica aprendida

**Não inferir imagem vs vídeo pelo nome do criativo nem pela dimensão.**

Mesmo um criativo chamado `Feed` e 1080x1080 pode abrir o modal de download como `Vídeo MP4`. A classificação correta para download vem do próprio Canva:

1. abrir URL da pasta;
2. clicar nos três pontinhos do criativo;
3. clicar em `Baixar`;
4. manter o formato que o Canva pré-selecionou;
5. clicar no botão roxo `Baixar`;
6. classificar depois pelo arquivo baixado real (extensão/MIME/dimensão/duração).

## Estrutura local recomendada

```text
canva-local-automation/
├── package.json
├── README.md
└── scripts/
    ├── login-check.js
    ├── folder-audit.js
    └── folder-download-pilot.js
```

Scripts npm úteis:

```json
{
  "scripts": {
    "setup": "npx playwright install chromium",
    "login": "node scripts/login-check.js",
    "audit": "node scripts/folder-audit.js",
    "download:pilot": "node scripts/folder-download-pilot.js",
    "download:v2": "node scripts/folder-download-v2.js",
    "download:from-manifest": "node scripts/folder-download-from-manifest.js"
  },
  "dependencies": {
    "playwright": "^1.57.0"
  }
}
```

Notas:

- `download:pilot`: somente 3–5 itens para validar seletores; não é final para pastas grandes se salvar só por nome.
- `download:v2`: versão automática com rolagem lenta e `safeName(nome)__designId.ext`; útil quando a coleta retorna o total esperado.
- `download:from-manifest`: preferido para retomar pasta grande quando já existe lista-mestre de `designId`; usa manifest antigo como fonte, copia OKs de V2 e baixa apenas faltantes/erros em `downloads_V3`. Não usar como primeiro comando de pasta nova sem manifest fonte válido.
- `download:visible`: modo assistido por tela visível; usar só para diagnóstico/resgate pequeno, não como plano principal de pastas 200+ itens porque Rodolfo não quer ficar babysitting no PC.
- Para pasta nova, gerar/coletar primeiro com `download:v2` ou audit. Se Rodolfo pedir “com 999 na frente”, lembrar que `999` pode virar nome/pasta de saída conforme assinatura do script; depois validar o JSON real e não assumir que foi limite.
- Para grandes backlogs, manter uma lista-mestre (`name`, `designId`) separada do manifest de download; se o arquivo fonte zerar/perder, recriar por script seed com dados compactados em vez de colar JSON gigante no chat.

## Sequência segura

1. `npm install`
2. `npm run setup`
3. `npm run login` — abre Chromium local; Rodolfo faz login e código manualmente.
4. `npm run audit -- "URL_DA_PASTA"` — captura JSON/screenshot com lista de designs e modal aberto, sem baixar.
5. Confirmar que o audit mostra:
   - `Mais ações: <nome>` por design;
   - menu/modal `Baixar`;
   - botão `Formato de arquivo`;
   - botão final `Baixar`.
6. Rodar piloto pequeno: `npm run download:pilot -- "URL_DA_PASTA" 3`.
7. Verificar `output/download-pilot-manifest.json` e `output/downloads/` antes de escalar.

## Guardrails

- Começar sempre com limite pequeno (3–5 criativos), nunca pasta inteira.
- Não apagar, mover ou alterar designs no Canva.
- Não depender de nomes para separar IMG/VID.
- Baixar bruto primeiro; organizar local/Drive depois.
- Registrar manifest com: nome, designId, formato Canva, arquivo baixado, status, erro.
- **Nunca salvar arquivo usando só o nome do criativo**: em pastas grandes há muitos nomes repetidos e o Windows sobrescreve arquivos. Usar sempre `safeName(nome)__designId.ext`.
- Se o Discord não anexar pacote zip/tar, colar arquivos completos no chat em blocos de código.

## Pastas grandes: retomada, nomes repetidos e rolagem

Aprendizado operacional em GEORGE/NICOLAS: listas grandes do Canva usam virtual scroll; scripts que coletam 200+ itens e depois tentam reencontrar botões por nome podem falhar após muita rolagem (`Mais ações` não encontrado). Além disso, nomes repetidos como `50 - Story Espanhol` sobrescrevem arquivos se o `designId` não estiver no nome.

Padrão correto para pastas grandes:

```text
Problema                         | Regra
---------------------------------|--------------------------------------------------
Nomes repetidos                  | nome do arquivo sempre inclui designId
Timeout depois de muita rolagem  | usar fluxo resumível por designId/busca, não nome
Execução longa                   | preferir automação unattended; evitar exigir Rodolfo no PC
Falha no meio                    | ler manifest e pular status OK com arquivo existente
Auditoria final                  | comparar designs coletados vs manifest OK vs arquivos únicos
```

Modos aceitáveis:

1. **download:v2** — automático com rolagem lenta e nome seguro; aceitar só se a coleta retornar perto do total esperado da pasta.
2. **download:from-manifest** — preferido para GEORGE/NICOLAS ou pastas grandes quando já existe lista-mestre de `designId`; não depende de redescobrir todos os itens pela rolagem inicial, copia OKs anteriores e retoma faltantes/erros.
3. **download:visible** — assistido por blocos visíveis, útil só para diagnóstico ou resgate pequeno; não é adequado como plano principal para 200+ itens porque Rodolfo não quer ficar babysitting.
4. **download:search-resume** — opção futura quando disponível: usa lista de `designId`, busca/filtra item, baixa, registra e retoma sozinho.

Pitfall de comando: nunca mande Rodolfo rodar um npm script antes de entregar o arquivo correspondente e a linha em `package.json`; ele vai receber `Missing script`. Ao introduzir novo modo, envie sempre “arquivos a atualizar” antes do comando.

Antes de subir ao Drive, validar:

```text
Validação                     | Esperado
-----------------------------|-----------------------------
manifest total               | igual ao número de designs
status OK                    | igual ao número de designs
arquivos únicos no disco     | igual ao status OK
arquivos com __designId.ext  | 100%
erros                        | 0 ou lista explícita para retry
```

## Seletores/heurísticas observadas

Em pasta/lista do Canva em PT-BR:

- Botão por item: role button com nome `Mais ações: <nome do criativo>`.
- Item de menu: texto exato `Baixar`.
- Modal: título/texto `Baixar`, botão `Formato de arquivo`.
- Formatos visíveis: `Vídeo MP4`, `PNG`, `JPG`, `GIF`, `PDF padrão`, `PDF para impressão`.
- Botão final: `Baixar` com largura grande no modal.

## Pós-download

Depois do download, classificar por evidência real:

```text
IMG/VID       -> extensão + MIME + ffprobe/file quando disponível
Feed/Story    -> dimensão/aspect ratio do arquivo baixado
Idioma        -> nome + OCR/texto quando necessário
Incertos      -> REVIEW
```
