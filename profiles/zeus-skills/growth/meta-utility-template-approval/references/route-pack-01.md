## Overview

Use this skill for the MGS workaround after Meta/Facebook blocked the old post-24h broadcast tag route. The operating path is to send broadcast-like Messenger messages through Utility Template-style copies that must be approved by Meta.

Operational facts from Rodolfo + SB/Ciro/Felipe context:

- MGS sends **12 messages per day per Facebook page**.
- Approval is effectively by **copy/message + page**.
- The same copy can approve across many pages; if it approves in one page, chance is high that it approves in the rest, but this must still be validated at scale.
- The goal is to build a reusable bank of roughly **200 approved messages per page** so daily rotation has enough supply.
- Copy approval is an iterative scale game: send a batch, keep what approves, use approved messages as references, remove/rewrite rejects, repeat until enough approved copies exist.
- Current safe scope: **text + button only**. No image, second message, or dynamic-value optimization until the basic delivery layer is stable.

The purpose is not to create the most aggressive copy. The purpose is to maximize approved inventory while preserving delivery, compliance resilience, and performance.

## When to Use

Use when Rodolfo asks to:

- generate or rewrite Messenger broadcast/BD copies after the 24h tag block;
- create Utility Template-style CSV batches;
- use approved copies as positive examples to generate more;
- analyze approved vs rejected copies from dashboard export;
- plan how many copies/templates are needed per page/site/language;
- decide whether to modify an existing template or create a new template;
- document the dashboard workflow around `Run Approvals`;
- create operating instructions for contractors to produce approval batches.

Do not use for:

- Meta Ads campaign setup or pixel work — route to Ares/Meta skills;
- WordPress quiz/SMS funnel tracking — route to quiz/SMS skills;
- editorial REC/P1 production — route to Atena/content skills.

## Glossary

```text
Template    Conjunto de mensagens no manager/dashboard.
Copy        Mensagem individual dentro do template.
Page        Página Facebook/Messenger onde a copy precisa aprovar.
Approval    Resultado de aprovação da copy para página(s).
Hash        Identificador da copy; ao alterar o texto, o hash muda e o approval reseta.
Fallback    Se uma copy reprovar, sistema pode usar outra copy aleatória aprovada.
Run Approvals  Botão do dashboard que submete mensagens para aprovação/teste imediato.
```

## Core Operating Model

Meta não está liberando o antigo broadcast pós-24h como antes. O novo modelo operacional é:

```text
Criar lote de copies utility-shaped
→ subir/importar no template
→ vincular o template a pelo menos 1 página
→ rodar Run Approvals
→ dar F5 no dashboard para atualizar status
→ separar aprovadas/reprovadas
→ usar aprovadas como referência para gerar novas
→ remover/reescrever reprovadas
→ repetir até formar banco de ~200 aprovadas por página
→ escalar para as demais páginas do nicho/site/idioma
```

Regra de escala:

```text
1 página usa 12 mensagens/dia.
Banco alvo: ~200 mensagens aprovadas por página.
Com 200 aprovadas, a operação tem rotação suficiente para vários dias sem repetir demais.
```

## Dashboard Workflow

1. Abrir `https://app.smartbiddingdigital.com/accounts`.
2. Selecionar o contexto/fonte **Messenger** no topo.
## Dashboard Workflow

1. Abrir `https://app.smartbiddingdigital.com/accounts`.
2. Selecionar o contexto/fonte `Messenger` no topo quando aplicável.
3. Usar a tab `Page` para ver páginas Facebook/Messenger e campos de template instalado.
4. Usar a tab `Broadcast Template` para ver/editar os templates instalados.
5. Abrir o template em Messenger Messages.
6. Confirmar `Template Name`, `Company`, idioma/site/nicho e links.
7. Importar ou criar mensagens no formato CSV esperado.
8. Se for template novo, garantir que ele esteja vinculado a pelo menos **1 página**.
9. Clicar em `Run Approvals`.
10. Aguardar o processo.
11. Dar **F5** na página do dashboard para atualizar os indicadores.
12. Ler a coluna `Approval`:
   - verde/aprovado: manter no banco positivo;
   - vermelho/rejected: remover ou reescrever;
   - invalid format: corrigir estrutura antes de reescrever copy.
13. Se o lote tiver boa taxa de aprovação, escalar para mais páginas/templates.
14. Se o lote reprovar muito, usar apenas as aprovadas como seed para novo lote.

Importantíssimo: alterar qualquer copy reseta o approval porque muda o hash. Não editar copy aprovada sem motivo.

Auth/dashboard pitfall: when automating SB login from 1Password, concealed `password` fields must be retrieved with `op ... --field password --reveal`. If Auth0 succeeds but the app logs `BotGuardError: Automated browser detected`, diagnose it as SB anti-automation/headless detection, not bad credentials. **Do not use Playwright headless as the default path for SB. Use headed Playwright via `xvfb-run` with `headless=False`, `--disable-blink-features=AutomationControlled`, normal Chrome user-agent, and persistent `storage_state` at `/tmp/smartbidding_state_headed.json`.** See `references/smartbidding-dashboard-navigation-and-botguard-2026-06-29.md`.

SB dashboard implementation notes observed in the frontend bundle:

```text
Messenger tabs: Account / User / Page / Broadcast Template
Relevant calls: /campaigns/messenger/reinstall_bot_template, /campaigns/messenger/bot_templates, /broadcast/messenger/{id}/approve
```

Use these endpoints as orientation, not as proof of current runtime data; validate authenticated access/API responses before automating.

## Batch Strategy

### Target

```text
Por página: 12 envios/dia
Banco ideal: ~200 approved copies por página
Lote inicial recomendado: 50–150 copies por vertical/idioma
Loop: aprova → retém → gera semelhantes → aprova de novo
```

### Practical loop

1. Comece com um CSV de copies já aprovadas, se existir.
2. Gere um lote novo copiando estrutura, intenção e tom das aprovadas — não claims específicos inventados.
3. Rode aprovação em 1 página.
4. Se 60%+ aprovar, já existe caminho; preserve aprovadas e reescreva reprovadas.
5. Se 80%+ aprovar, use o lote como base para escalar e produzir variações.
6. Repita até atingir cerca de 200 aprovadas por página ou por cluster de páginas onde a mesma copy aprova.

### What to track

```text
Site/vertical
Idioma/país
Template name
Page tested
Batch ID/data
Total submitted
Approved
Rejected
Invalid format
Approval rate
Copies promoted to approved bank
Copies removed/rewrite needed
Performance 24h/48h after use
```

## CSV Format

Expected columns observed in the dashboard/export:

```csv
MESSAGE ID,TEXT,DESCRIPTION,IMAGE,CTA 1,LINK 1,CTA 2,LINK 2,TEXT 2
1,"Message text here",,,CTA TEXT,https://example.com/path,,,
```

Current operating constraints:

- `TEXT` is the main copy.
- `CTA 1` is the button label.
- `LINK 1` is the destination.
- Phase 1 is text-only: keep `IMAGE`, `CTA 2`, `LINK 2`, `TEXT 2` empty until Ciro explicitly ships image/media support in both SB front end and back end.
- Do not rely on `{{first_name}}` in Phase 1 batches; if Messenger User Profile API / `pages_messaging` / page subscription / SB profile sync fails, the message can render with a blank or literal placeholder. Write copy that reads cleanly without personalization.
- Keep one message per row.
- Keep message IDs sequential.
- Do not add extra columns unless dashboard import supports them.
- If emojis are present, export the dashboard-import CSV as **UTF-8 with BOM** (`utf-8-sig`) and CRLF. If mojibake appears (`âœ…`, `ðŸš€`, `Itâ€™s`), do not remove emojis by default; first regenerate the import CSV with BOM and compare against a known-good emoji CSV.

