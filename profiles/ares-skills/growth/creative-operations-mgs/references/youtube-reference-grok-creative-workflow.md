# YouTube reference + GPT/Grok creative workflow — Ares

Use this when Rodolfo/Kelly/Geizian asks for a creative/video inspired by a YouTube Shorts/Reels reference and/or asks for versions with GPT and Grok.

## Core rule learned

Do **not** start producing a new creative when a required reference or backend is blocked. First resolve or report the blocker. If the user supplied a reference and asked to be inspired by it, the reference must be actually viewed/analyzed or the limitation must be explicit before generation.

Bad flow:

```text
YouTube blocked → infer from memory/thumbnail only → generate anyway → user rejects quality.
```

Correct flow:

```text
1. Try to access/analyze the reference with tools.
2. If blocked, try alternative technical routes.
3. If still blocked, report the exact blocker and ask for the missing prerequisite.
4. Only generate after reference/backend is usable, unless the user explicitly authorizes proceeding from partial reference.
```

## YouTube/Shorts reference ingestion checklist — fluxo atual Ares

Rodolfo logou no perfil Chromium persistente do Ares. YouTube/Shorts **não deve bloquear produção automaticamente** antes de tentar o fluxo autenticado.

Perfil persistente:

```text
/root/.hermes/profiles/ares/browser-profiles/youtube-chromium
```

Scripts canônicos:

```text
/root/mgs-agent/scripts/ares-youtube-persistent-browser.py
/root/mgs-agent/scripts/ares-youtube-reference-download.sh
/root/mgs-agent/scripts/ares-youtube-capture-frames.py
/root/mgs-agent/scripts/ares-youtube-login-browser.sh
```

Para qualquer URL de referência YouTube/Shorts, faça nesta ordem:

```bash
/root/mgs-agent/scripts/ares-youtube-reference-download.sh '<URL>' '<OUT_DIR>'
```

Se o download via `yt-dlp` falhar por signature/formats/login, usar captura pelo Chromium persistente:

```bash
xvfb-run -a /root/mgs-agent/scripts/ares-youtube-capture-frames.py '<URL>' --headed --out-dir '<OUT_DIR>'
```

Depois:

1. analisar `status.json`, frames e/ou `contact_sheet.jpg`;
2. usar `vision_analyze` nos frames/contact sheet antes de criar vídeo/imagem final;
3. transformar a referência em linguagem visual concreta: ritmo, cortes, hierarquia, paleta, movimento, composição, tipografia, duração e momentos-chave;
4. só então gerar o criativo final.

Status de validação real já feito no Shorts:

```text
URL: https://www.youtube.com/shorts/PCdygSACl_4
Status YouTube: OK
Duração: 15.041s
Stream: blob carregado
readyState: 4
Frames capturados: 8 frames + contact_sheet
Path: /root/mgs-agent/data/ares/creative-ops/references/daniel-safari/youtube-auth-frames/PCdygSACl_4/
```

Se a referência ainda não abrir via Chromium persistente, pare e reporte blocker com evidência curta. Próximas opções a pedir ao Rodolfo: renovar login do perfil, cookies persistentes ou anexo do vídeo.

## Datacenter/browser anti-bot pitfall

Rodolfo pode abrir um Shorts em navegador residencial enquanto VPS/Playwright falha. Isso costuma ser reputação de IP/browser/headless/datacenter, não necessariamente privacidade do vídeo.

Não peça cookies por vídeo. Primeiro use o perfil Chromium persistente acima. Se cookies forem necessários, usar armazenamento seguro; nunca colar cookies no Discord nem imprimir conteúdo.

Cookie path legado/alternativo quando necessário:

```text
/root/.hermes/profiles/ares/secrets/youtube-cookies.txt
```

Longer-term robust solution: use a browser/proxy backend with residential IP/reputation when recurring YouTube references are part of Creative Ops.

## GPT + Grok split

When the user asks for `GPT` and `Grok` versions:

```text
GPT/OpenAI: use image_generate / OpenAI-Codex path for static visual base when configured.
Grok/xAI: use /root/mgs-agent/scripts/mgs-grok-generate.py for explicit Grok media generation.
```

Before promising Grok output, validate xAI auth/backend:

```bash
HERMES_HOME=/root/.hermes/profiles/ares hermes auth status xai-oauth
python3 /root/mgs-agent/scripts/mgs-grok-generate.py image --profile ares --prompt 'small test' --aspect-ratio 9:16 --output-dir /tmp/ares-grok-test
```

If xAI OAuth is missing/broken, reauthenticate via Hermes model picker rather than fabricating a Grok version:

```text
HERMES_HOME=/root/.hermes/profiles/ares hermes model --manual-paste --refresh
provider: xAI Grok → xAI Grok OAuth → Reauthenticate
```

The user opens the xAI auth URL and returns either the failed callback URL or bare code. After auth, validate with a real Grok generation.

## User-experience rule from Rodolfo

If a prerequisite blocks the requested creative — reference video, Grok auth, Drive/Canva access, etc. — report it immediately and ask to resolve it. Do not generate an approximate/placeholder creative and only later reveal that the reference/backend was blocked.

## Quality expectation for video invitations

For family/event invitation videos, especially when the user rejects a draft as low quality:

- Use the supplied reference as structural inspiration: layout, motion rhythm, hierarchy, and visual language.
- Keep event data fixed and readable unless the reference clearly uses another pattern and the user approves it.
- Music must be specific to the theme/occasion; placeholder vague loops are not acceptable.
- Clearly label versions by backend: `GPT/OpenAI` and `Grok/xAI`.
- Validate output visually with frames before sending.
