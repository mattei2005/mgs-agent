# Meta/Facebook Ad Library — Playwright Browser Download

## Quando usar

Use quando Rodolfo pedir para abrir a Facebook/Meta Ad Library pelo “primeiro modo”/browser automatizado, baixar criativos de uma busca ou confirmar se a VPS consegue ver a Library sem depender da API `/ads_archive`.

## Aprendizado operacional

A Meta pode retornar `HTTP 403`/challenge para `curl` ou acesso HTTP direto, mas ainda assim a página pode renderizar corretamente via Chromium/Playwright. Não conclua bloqueio definitivo só pelo `curl` quando o objetivo é crawler visual.

Validação mínima deve testar o caminho real de browser:

```text
1. Abrir a URL da Library com Playwright/Chromium.
2. Aguardar DOM/content e fazer scroll para lazy-load.
3. Validar sinais de acesso útil:
   - título/HTML da Meta Ad Library;
   - contagem de resultados;
   - cards com `Library ID`;
   - imagens CDN carregadas;
   - vídeos com `currentSrc`/dimensões quando existirem.
4. Baixar pelo menos uma imagem ou vídeo via browser context/request.
5. Salvar screenshot/prova local e resumir sem expor URLs sensíveis completas.
```

## Interpretação de resultados

```text
Sinal observado                         Interpretação
──────────────────────────────────────  ─────────────────────────────────────────────
`curl` retorna 403 challenge             Não prova bloqueio do browser; testar Playwright.
Playwright mostra resultados/cards       Caminho de coleta visual está viável.
Imagens `scontent/xx.fbcdn.net` 200      Download de IMG como referência bruta viável.
Vídeo `.mp4` em `video-*.fbcdn.net` 200  Download de VID como referência bruta viável.
`/ads_archive` code 10/subcode 2332002   Token pode estar válido, mas app sem permissão Ad Library.
```

## Prova de vida recomendada

Reporte compacto:

```text
IP/provedor/localização detectada
Acesso HTTP cru/curl: OK ou 403/challenge
Browser/Playwright: OK ou bloqueado
Resultados visíveis: contagem aproximada
Cards/IDs lidos: primeiros IDs
IMG teste: HTTP, mime, dimensão, bytes
VID teste: HTTP, mime, bytes/duração se disponível
Screenshot: path local ou validação visual
```

## Segurança e compliance

- Baixar criativos da Library apenas como **referência/inspiração bruta**, não como asset final copiado.
- Antes de qualquer uso interno, adaptar layout/copy/claims/marca e passar pelo sanitizer oficial.
- Não colar URLs CDN enormes com querystrings no Discord quando não forem necessárias.
- Não expor token/cookie/sessão; usar browser profile/context e reportar só status.

## Sanitização

Todo arquivo baixado para virar asset interno precisa passar pelo gate oficial:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/file --agent ares
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/file.metadata-clean.ext
```

Se o sanitizer remover `harmful_tags` mas `verify` ainda retornar `clean=false` em alguma classe de mídia, isso é pendência de sanitizer/allowlist antes de tratar como asset final; reporte como infraestrutura quando tiver alteração de pacote/script/config.
