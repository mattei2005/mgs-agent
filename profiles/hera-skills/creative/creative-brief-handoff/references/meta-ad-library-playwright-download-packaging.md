# Meta Ad Library — Playwright download + packaging workflow

## Quando usar

Use quando Rodolfo pedir para abrir a Meta/Facebook Ad Library pelo “primeiro modo”/browser, baixar criativos visuais, vídeos ou montar um ZIP de referências.

## Lições operacionais validadas

- `curl`/HTTP cru pode continuar retornando `403` com challenge mesmo quando o browser automatizado consegue renderizar a Library. Não pare no `curl` se o pedido é visual/download; valide com Playwright/Chromium.
- O caminho eficaz é Chromium/Playwright com contexto realista: user-agent de Chrome desktop, locale `en-US`, timezone `America/New_York`, headers de idioma e pequenos ajustes anti-`navigator.webdriver`.
- Depois que a página renderiza, a Library carrega assets em `scontent-*.xx.fbcdn.net` e `video-*.xx.fbcdn.net`. Extraia URLs de `img.currentSrc/src` e `video.currentSrc/src`, não copie apenas thumbnails.
- Para anúncios repetidos/virtualizados, dedupe por `library_id` e URL de mídia. Se o usuário pedir “os primeiros N”, use a ordem visual dos cards renderizados.
- Sempre incluir `README.txt` + `inventory.json` no ZIP para rastrear origem, tipo, dimensões, arquivo, hash e status de limpeza.
- Tratar tudo como **referência/inspiração criativa**, não asset para copiar direto em campanha.

## Fluxo recomendado

1. Montar URL da Library com busca/filtros solicitados.
2. Abrir com Playwright/Chromium e aguardar `Library ID`, resultados e mídia carregarem.
3. Scroll incremental até ter N cards/mídias suficientes.
4. Extrair:
   - `Library ID` do card mais próximo;
   - texto/copy visível do card;
   - `img.currentSrc` para imagens;
   - `video.currentSrc` para vídeos MP4;
   - dimensões naturais (`naturalWidth/naturalHeight` ou `videoWidth/videoHeight`).
5. Baixar mídia via `context.request.get(url)` mantendo o mesmo contexto do browser.
6. Nomear como referência, ex.:
   - `UTUA_LIBRARY_REF_01_IMAGE_<library_id>.jpg`
   - `UTUA_LIBRARY_REF_VIDEO_01_<width>x<height>.mp4`
7. Rodar sanitizer oficial:
   - `/root/mgs-agent/scripts/clean-creative-metadata.sh batch raw --out-dir clean --agent hera`
   - verificar cada arquivo com `verify` antes de empacotar.
8. Criar pacote:
   - `creatives/` ou `videos/` com arquivos limpos;
   - `README.txt` alinhado curto;
   - `inventory.json` com hashes, dimensões e `clean=true`.
9. Validar ZIP com `unzip -l` e reportar quantidade, tipos, `harmful_tags_after=0` e `sha256`.

## Pitfalls

- Não declare bloqueio apenas porque o status inicial da navegação ou `curl` retornou `403`; a página pode executar o challenge e carregar resultados no browser.
- Não enviar arquivos brutos baixados da CDN. Entregar apenas a pasta/ZIP com versões verificadas limpas.
- Se o sanitizer marcar JPEG com apenas `JFIFVersion` residual após limpeza, isso é metadado estrutural JFIF, não privacy metadata; o gate deve permitir como structural allowlist.
- Vídeos MP4 podem manter campos QuickTime/Track estruturais; se `verify` retorna `clean=true`, isso é aceitável.
- Se uma tentativa nova de coleta não encontrar vídeos por virtualização/scroll, usar URLs MP4 capturadas de uma sessão browser renderizada válida ou repetir o scroll com player realmente carregado (`readyState > 0`, dimensões não-zero).

## Comunicação ao Rodolfo

Resposta final deve ser operacional e curta:

```text
Pacote
────────────────────────────────────────────────────────
Arquivo            <zip>
Quantidade         <N> imagens/vídeos
Inventário         README.txt + inventory.json dentro do ZIP
Sanitização        clean=true nos <N> arquivos
harmful_tags_after 0 nos <N> arquivos
SHA256             <hash>
```

Anexar com `MEDIA:/path/to/file.zip`.