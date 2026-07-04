# SB Broadcast Template API Update Pattern

Sessão: 2026-06-30, redução de 13 templates US-CC-EN para melhores 70 mensagens.

## Quando usar

Use este padrão quando a UI da SB seria lenta/instável para editar/importar vários Messenger Broadcast Templates, mas a SPA já está autenticada e expõe `/broadcast/Messenger`.

## Técnica

A SPA usa:

```text
GET  /broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
POST /broadcast/Messenger
```

O `POST /broadcast/Messenger` salva o template completo. Para atualizar mensagens:

1. Entrar na SB com Playwright headed/Xvfb e storage state válido.
2. Navegar até `Messenger > Broadcast Template` para a SPA disparar a request real.
3. Capturar a response do GET `/broadcast/Messenger` e também os headers da request real.
4. Localizar o template por `NAME` exato.
5. Fazer backup do row completo (JSON) e de `MESSAGES` em CSV humano.
6. Alterar apenas `MESSAGES` no payload do template.
7. Enviar `POST https://api.jbfdigital.com.br/broadcast/Messenger` com o payload completo alterado e headers/auth capturados internamente.
8. Reconsultar GET `/broadcast/Messenger` e validar contagem/conteúdo.

Keep the Playwright/browser/context lifetime open across steps 3–8. Do not return `ctx/page` from inside `async with async_playwright()` and use it later; the context will already be closed and `ctx.request.post(...)` can fail with `TargetClosedError`. Use `p = await async_playwright().start()` and close `browser`/`p` only after all POSTs and validation complete. See `references/sb-spa-api-playwright-lifetime-and-ad-hoc-verification-2026-06-30.md`.

## Pitfall: `ctx.request` direto pode dar 401

Chamadas diretas do `APIRequestContext` sem os headers/auth da SPA podem retornar `401 Unauthorized`, mesmo com a página logada. A solução validada foi capturar uma request real feita pela página e reaproveitar os headers internamente no `ctx.request.post/get`.

Não imprimir cookies, bearer tokens, Authorization, session headers ou storage state no chat/log final.

## Payload de mensagens

No row retornado por `/broadcast/Messenger`, `MESSAGES` pode vir como string JSON. Parse antes de editar:

```python
msgs = json.loads(row['MESSAGES']) if isinstance(row['MESSAGES'], str) else row['MESSAGES']
```

Campos observados para Messenger Broadcast Template:

```text
MESSAGE_ID
TEXT
DESCRIPTION
IMAGE
CTA_1
LINK_1
CTA_2
LINK_2
TEXT_2
APPROVED / INVALID_FORMAT / REJECTED / ERROR (quando já houve approval)
```

Ao salvar lista nova, renumerar `MESSAGE_ID` sequencialmente se a importação/API espera sequência limpa. Preserve `TEXT`, `CTA_1`, `LINK_1` quando o objetivo for reduzir/selecionar mensagens existentes.

## Validação mínima

Antes de reportar sucesso:

- POST retornou 2xx/201;
- GET pós-save retorna o template;
- `len(json.loads(MESSAGES))` bate com o alvo;
- primeiro/último texto/link fazem sentido;
- backups JSON + CSV existem;
- auditoria local registra template, ID, before/after, backups e validação.
