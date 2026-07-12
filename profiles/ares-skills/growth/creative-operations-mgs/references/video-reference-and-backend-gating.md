# Gate de referência externa + backend específico para vídeos criativos

## Quando aplicar

Use em pedidos de vídeo criativo quando o usuário fornecer referência externa ou exigir comparação/produção em backends específicos, por exemplo:

- “faz uma versão com GPT e outra com Grok”;
- “use este YouTube Shorts/Reels/TikTok como referência”;
- “quero nesse estilo”; 
- “não quero resposta de que não conseguiu, resolva o acesso primeiro”.

## Lição operacional

Não produza uma versão final “no escuro” quando a referência ainda não foi visualizada ou quando um backend exigido ainda não foi validado. Isso gera retrabalho e quebra a expectativa do usuário.

O fluxo correto é:

```text
1. Validar acesso à referência.
2. Extrair vídeo, frames ou pelo menos thumbnails/metadados suficientes.
3. Confirmar que a referência foi realmente analisada.
4. Validar cada backend solicitado.
5. Se algum requisito bloquear, reportar o bloqueio e a ação necessária.
6. Só então produzir a peça ou seguir com fallback explicitamente aprovado.
```

## YouTube Shorts — escada de tentativas

Quando a referência for YouTube Shorts:

```text
Tentativa                         Evidência esperada
────────────────────────────────  ─────────────────────────────────────────────
yt-dlp padrão                     arquivo de vídeo ou erro claro
yt-dlp com clients alternativos   web_embedded, ios, android, tv
YouTube oEmbed                    título, canal, thumbnail_url
Thumbnails ytimg                  maxres/sd/hq para análise parcial
Playwright/Chromium               screenshot/status do player
ytInitialPlayerResponse           playabilityStatus, streaming/storyboards se houver
Frontends alternativos            Piped/Invidious, quando disponíveis
```

Se o YouTube retornar `LOGIN_REQUIRED`, `Sign in to confirm you’re not a bot` ou o embed retornar `Error 153`, não declare que analisou o vídeo completo. Informe que só há fallback parcial se thumbnails/oEmbed foram obtidos.

## Grok/xAI

Para Grok explícito:

```text
1. Usar o wrapper oficial MGS quando disponível:
   /root/mgs-agent/scripts/mgs-grok-generate.py

2. Validar autenticação antes de prometer entrega:
   hermes auth status xai-oauth

3. Se o wrapper retornar `No xAI credentials available for this profile` ou o auth indicar `logged out/missing access_token`, parar e pedir reautenticação/configuração aprovada.
```

Nunca rotule uma versão GPT/OpenAI, local/ffmpeg/Pillow ou fallback como “Grok”.

## Como reportar bloqueio sem parecer desistência

A resposta deve ser curta, operacional e com próxima ação clara:

```text
Status: bloqueado para cumprir exatamente o pedido.
O que consegui validar:
- [comando/tentativa] → [resultado]
- [fallback parcial, se houver]

Para destravar:
- [cookie/sessão/anexo necessário]
- [auth Grok/xAI necessário]

Não vou produzir a versão final até a referência/backend estarem validados ou você aprovar fallback.
```

## Pitfall

Se o usuário corrige “não comece quando não conseguir algo; reporte para resolver”, isso deve prevalecer sobre a tendência de entregar um rascunho. Para esse tipo de pedido, rascunho sem referência validada é pior do que bloqueio honesto.
