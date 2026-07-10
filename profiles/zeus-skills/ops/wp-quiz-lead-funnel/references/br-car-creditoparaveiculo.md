# BR/CAR — creditoparaveiculo.com

## Context

First MGS WordPress quiz lead funnel migrated from Lovable/Supabase into a first-party WordPress plugin.

- Country: BR
- Vertical: CAR / crédito veicular
- Site: `creditoparaveiculo.com`
- Plugin: `mgs-quiz-carro`
- Purpose: capture financing leads, route to SMS Funnel by gestor, then redirect to REC page preserving UTMs.

## Runtime e modelos visuais

`creditoparaveiculo.com` usa o plugin de quiz `mgs-quiz-carro`; não há plugin de chat nesse site. Quando Rodolfo disser “chat” informalmente sobre essas URLs, confirmar o produto real no runtime e tratar o pedido como quiz, sem envolver `mgs-chat-funnels`.

Versão validada em produção em 2026-07-10: `mgs-quiz-carro` v1.6.0.

Correções operacionais v1.6.0:

- `Nome/label` e `URL add-lead` no editor da quiz são somente leitura. O operador escolhe apenas o gestor no seletor; o backend resolve os dados server-side para evitar erro humano ou adulteração de POST.
- O menu MGS Quiz possui submenu `SMS`, página central para gerenciar os presets G001–G006. A fonte central é a option `mgs_quiz_sms_presets`, com os valores canônicos do plugin apenas como fallback inicial.
- Salvar a página SMS exige label não vazio e URL HTTPS para todos os gestores. A alteração deve ser propagada para todas as linhas `sms_funnel_urls` das quizzes com o mesmo `gestor_code`, mantendo o runtime REST em paridade com a fonte central.
- O editor da quiz não oferece modo manual e exige uma seleção válida de gestor antes de salvar.

Correção operacional v1.5.3:

- Quando a quiz usa seletor único de gestor/SMS, não exibir controles redundantes de multi-lista (`Usar este`, `+ Adicionar gestor` ou `Remover`). Manter apenas o seletor canônico e, abaixo, os campos preenchidos para conferência/edição manual; o índice default pode ser enviado como hidden `0`.

Correções operacionais v1.5.2:

- O admin oferece um seletor `Gestor / lista SMS Funnel` com os presets canônicos G001–G006. Ao escolher um gestor, a UI preenche automaticamente código, nome/label e URL add-lead.
- No salvamento, o código selecionado é resolvido server-side contra os presets canônicos; não confiar apenas nos campos preenchidos por JavaScript. A configuração persistida deve conter exatamente uma linha ativa e default para a quiz.
- Configs antigas com várias linhas são normalizadas visualmente para a linha marcada como default; ao salvar pelo seletor, são persistidas como escolha única.

Correções operacionais v1.5.1:

- A listagem de quizzes deve exibir a linha SMS marcada como `default=1`; nunca assumir que `sms_funnel_urls[0]` é a selecionada. Se não houver `default` legado, usar a primeira linha ativa, em paridade com o fallback do backend.
- A duplicação deve copiar a configuração, gerar novo `id`, nome e slug, limpar os links SMS para escolha explícita e redirecionar para `admin.php?page=mgs-quiz-new&id=<novo-id>&duplicated=1` somente após confirmar que `$wpdb->insert()` teve sucesso.
- A tabela `wp_mgs_quiz_config` não possui coluna `created_at`. Incluir `created_at` no insert de duplicação faz o insert falhar e abre uma tela de quiz vazia apontando para um ID inexistente. Nunca inserir colunas sem validar o schema real; em falha, registrar `$wpdb->last_error` no log e retornar erro na listagem.
- As rotas públicas são rewrites virtuais do WordPress; não existem pastas físicas por quiz. Alterar a slug muda a chave no banco. A versão 1.5.1 não mantém histórico nem cria redirect automático da slug antiga; sem config correspondente, a URL antiga cai no comportamento normal do WordPress/site.

Modelos disponíveis no campo admin `Modelo visual`:

- `layout_template` vazio — Quiz padrão, pergunta primeiro e formulário depois.
- `fmybc_sms` — landing FMYBC/SMS com dados primeiro, checklist e badges.
- `quiz_maker_sb` — Quiz Maker SB, réplica first-party do layout de duas etapas da Smart Bidding: pergunta com opções verdes, depois nome/telefone, mantendo backend, SMS Funnel e redirect da MGS.

## Public Quiz Routes

Rotas confirmadas no banco em 2026-07-10:

- G001 — `/quiz-car-parcelas-g001/`
- G002/default — `/quiz-car-parcelas/`
- G003 — `/quiz-car-parcelas-g003/`
- G004 — `/quiz-car-parcelas-g004/`
- G005 — `/quiz-car-parcelas-g005/`
- G006 — `/quiz-car-parcelas-g006/`
- G007 — `/quiz-car-parcelas-g007/` (`layout_template=quiz_maker_sb`) — criada em 2026-07-10 com todos os dados internos clonados da G002/default, incluindo SMS Funnel, redirect, tracking, textos, opções e imagens; somente ID, nome, slug, modelo visual e `updated_at` diferem.
- Modelo FMYBC/SMS — `/quiz-car-002-g002/` (`layout_template=fmybc_sms`).

G002 is the default route without suffix. New campaign variants keep the sequential `gNNN` slug pattern unless Rodolfo defines a different campaign family.

## SMS Funnel Routing

Each gestor has its own SMS Funnel add-lead URL. Keep fallback blank when all gestor URLs are configured.

Do not expose full credentials/tokens in chat. SMS Funnel list URLs are operational integration URLs; display only when necessary and avoid dumping them unnecessarily.

Routing is validated by stored WP lead status:

- `ok:G001`
- `ok:G002`
- `ok:G003`
- `ok:G004`
- `ok:G005`
- `ok:G006`

For normal production quiz configs, the operator chooses **one SMS Funnel link per quiz** in the admin UI. That selected link is the destination for every lead from that quiz, regardless of UTMs/campaign/adgroup or whether the visitor returns later with a clean URL. Do not make UTM-based routing the normal behavior when a quiz-level SMS link is selected.

The SMS response body should include `success:true` and the expected `list_id` for the selected link.

## Redirect

Canonical final redirect:

`https://creditoparaveiculo.com/rec-br-financiamento-de-carro-sem-entrada/`

All incoming params must be preserved automatically: `utm_*`, `fbclid`, `gclid`, etc.

Redirect split UI should be business-facing:

- `+ Adicionar URL`
- URL field
- weight field
- remove action
- default 100 for single URL

## Admin UX Decisions

- Normal operator path for new variant: Duplicate → name → slug → choose one SMS Funnel link for the quiz (`Usar este`).
- The quiz-level selected SMS link wins for all submissions; do not expose normal operators to multi-condition routing by UTM.
- CSV import is technical/migration-only and should stay hidden behind advanced/details UI.
- Reports should show 5 days/leads by default, with per-page selectors.
- Tables should avoid narrow wrapping for gestor, SMS, phone.
- After saving an edit, redirect back to the same edit screen (`admin.php?page=mgs-quiz-new&id=<id>&saved=1`), not to the quiz list, so the operator keeps context.

## Known Interpretation

If WordPress records `ok:G00X` and SMS Funnel returns `success:true` with the correct `list_id`, but SMS Funnel dashboard still shows zero, treat it as likely SMS Funnel dashboard delay/cache/indexing/filter/deduplication unless contrary evidence appears.
