# Meta/Facebook Ad Library — Creative Intake e Download

## Quando usar

Use quando Rodolfo/Kelly pedir para analisar criativos da Facebook Ads Library, baixar referências, inventariar anúncios concorrentes ou transformar anúncios ativos em inspiração para a MGS.

## Decisão rápida: Playwright vs Meta API

```text
Caminho                    Melhor uso                                      Risco/limite
─────────────────────────  ──────────────────────────────────────────────  ─────────────────────────────
Chromium/Playwright         Mais rápido para tentativa visual imediata       Facebook pode aplicar challenge/403
Meta Graph /ads_archive     Melhor para inventário estável e paginado        Exige app/token com permissão do endpoint
Híbrido                     API lista + browser abre snapshot/CDN            Normalmente melhor para baixar mídia
Manual/semi-manual          Prints/links/IDs enviados por humano             Mais rápido se automação estiver bloqueada
```

Regra prática:

1. Se o objetivo for responder “consigo ver/baixar hoje?”, primeiro testar browser renderizado.
2. Se houver token Meta disponível, validar sem expor token: `/me`, `/me/adaccounts`, conta conhecida e `/me/permissions`.
3. Para Ad Library via API, testar `ads_archive` com `search_terms`, `ad_type`, `ad_reached_countries`, `fields` e `limit` baixo.
4. Se `/ads_archive` retornar `OAuthException code 10 / subcode 2332002` com mensagem `Application does not have permission for this action`, o token pode estar válido para Ads/Ares, mas o app não está liberado para Ad Library. Não trate como token expirado.
5. Se o erro for `OAuthException code 190 / subcode 463`, o token expirou; pedir renovação ou usar outro item/token autorizado.

## Campos úteis para `/ads_archive`

Exemplo conceitual de fields:

```text
id
page_id
page_name
ad_creation_time
ad_delivery_start_time
ad_delivery_stop_time
ad_snapshot_url
publisher_platforms
ad_creative_bodies
ad_creative_link_titles
ad_creative_link_descriptions
ad_creative_link_captions
```

Use `limit` baixo primeiro (ex.: 5) para validar permissão e evitar ruído/rate-limit.

## Download de criativos

A API pode retornar inventário e `ad_snapshot_url`, mas nem sempre entrega o arquivo de mídia direto. Para baixar imagem/vídeo, normalmente é preciso:

1. abrir/renderizar `ad_snapshot_url` ou a Library no browser;
2. extrair URLs de imagem/vídeo/CDN;
3. baixar os arquivos permitidos;
4. tratar como referência/inspiração, não como criativo final copiado;
5. passar todo arquivo baixado pelo sanitizador oficial antes de organizar/entregar.

## Segurança e comunicação

- Nunca imprimir access token, querystring com `access_token`, cookies ou headers sensíveis.
- Ao reportar validação de token, mostrar só: item 1Password, campo usado, `token_len`, endpoint, status e erro seguro.
- Se um output de API incluir URL com token em `paging.next`, não colar no Discord; resumir ou redigir.
- Deixar claro a diferença entre “token válido para contas de anúncio” e “app autorizado para Ad Library”.
- Tratar criativos da Library como benchmarking/inspiração; adaptar copy, layout, marca e claims antes de qualquer uso em campanha.

## Status operacional recomendado

```text
Resultado                                         Próxima ação
────────────────────────────────────────────────  ─────────────────────────────────────────
403/challenge na página pública                   Tentar Playwright/Chromium ou sessão válida
Token expirado code 190/subcode 463               Renovar token no 1Password
Token válido, /ads_archive code 10/subcode 2332002 App precisa permissão/liberação para Ad Library
API OK, snapshot disponível                       Inventariar e renderizar snapshots para mídia
Mídia baixada                                     Sanitizar metadata + inventariar como referência
```
