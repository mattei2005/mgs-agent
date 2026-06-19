---
name: meta-openzedfinanzas-replacement-clone
description: "Clone/replacement da campanha OpenzedFinanzas Meta Ads: estrutura real da campanha Patricia Flores loser, nomenclatura RPL, seleção de criativos vencedores, budget USD 25 e validações de clone."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, replacement, clone, openzedfinanzas, campaign-structure, mgs]
---

# Meta OpenzedFinanzas Replacement Clone

Use esta skill quando Rodolfo pedir para clonar/replacement de campanhas da conta Meta `OpenzedFinanzas-ES-CC-ES-03`.

## Conta/operação

```text
Campo              | Valor
-------------------|---------------------------------------------
Account ID         | 1356770869843984
Operação           | OpenzedFinanzas-CC-ES
Timezone           | Europe/Madrid
Métrica Europa     | MO = complete_registration
Custo              | CPMO = spend / MO
HOA alvo           | USD 2.00
Teto operação      | USD 300/dia
Reserva testes     | 20% = USD 60/dia
Budget campanha    | Máximo USD 25/dia inicialmente
```

## Campanha loser mapeada

Fonte real: `/root/mgs-agent/data/ares/meta-ads/audit/clone/inspect-campaign-120248290564280604.json`.

```text
Campo                  | Valor
-----------------------|--------------------------------------------------
Campaign ID            | 120248290564280604
Nome                   | Patricia Flores - US - ESP - (pg_22069) - 2
Status                 | ACTIVE
Objective              | OUTCOME_SALES
Buying type            | AUCTION
Bid strategy           | LOWEST_COST_WITHOUT_CAP
Budget original        | daily_budget=10000 cents (USD 100)
Special ad category    | FINANCIAL_PRODUCTS_SERVICES
Start original         | 2026-06-11T04:02:00+0200
Page token no nome     | pg_22069
```

## Estrutura real da campanha

```text
Adset ID             | Nome                   | Destination | Optimization         | Billing
---------------------|------------------------|-------------|----------------------|------------
120248290564350604   | Conjunto 01 - VÍDEOS   | MESSENGER   | OFFSITE_CONVERSIONS  | IMPRESSIONS
120248290564260604   | Conjunto 02 - IMAGENS  | MESSENGER   | OFFSITE_CONVERSIONS  | IMPRESSIONS
```

Targeting observado nos adsets:

```text
Campo                 | Valor
----------------------|------------------------------------------
País                  | ES
Idade                 | 18-65
Location types        | home, recent
Brand safety          | FACEBOOK_RELAXED, AN_RELAXED
Advantage audience    | targeting_automation.advantage_audience=1
Promoted object       | pixel_id 629060785934493, COMPLETE_REGISTRATION
Page ID promoted      | 1063171606876651
Attribution           | 7d click + 1d view
```

## Nomenclatura de replacement

Padrão criado para identificar trocas:

```text
<Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Exemplo:

```text
Patricia Flores - US - ESP - (pg_22069) - RPL - 20260619 - 01
```

Notas:
- `RPL` identifica replacement.
- `YYYYMMDD` é a data programada de início no timezone da conta.
- `seq` começa em `01`.
- Não reutilizar o sufixo numérico antigo da loser como identidade operacional do clone.

## Regras de clone

1. Clone deve ser criado PAUSED inicialmente, salvo autorização explícita para ACTIVE.
2. Start time deve ser o dia seguinte às `01:00` no timezone da conta; ao enviar em criação, converter com timezone real `Europe/Madrid` para ISO UTC `Z` (DST-aware), não usar offset fixo nem string local `+0200`.
3. Campaign daily budget nunca pode passar de `USD 25` inicialmente (`daily_budget=2500` cents).
4. Para clone-source/replacement, não começar com payload mínimo nem declarar campo “não encontrado”: primeiro fazer GET explícito completo da source e diff source-vs-payload nos níveis campaign/adset/ad.
5. Em conta Europa/UE de financeiro, adset pode exigir campos DSA/compliance diferentes de North America. Sempre puxar e copiar exatamente da source: `dsa_beneficiary`, `dsa_payor`, e qualquer campo com `dsa`, `beneficiary`, `payor`, `regulated`.
6. Selecionar exatamente 3 criativos vencedores da conta inteira, não só da campanha/página.
7. Ranking inicial de criativo vencedor: menor CPMO nos últimos 3 dias, com `spend >= USD 5` e `MO >= 2`.
8. Clone usa a mesma página/promoted object da loser, mas os criativos podem vir de outra campanha/página se forem vencedores da conta.
9. Depois do clone validado, loser deve ser deletada se a API permitir; se não permitir delete, arquivar/pausar.
10. Antes de reportar sucesso, validar com GET: campanha criada, status, budget, adsets e exatamente 3 ads.
11. Salvar audit em `/root/mgs-agent/data/ares/meta-ads/audit/clone/`.

### Checklist obrigatório antes de `POST /adsets` em EU/financeiro

```text
Campo / validação                         | Regra
------------------------------------------|------------------------------------------------------------
Source fields explícitos                   | Não confiar em default GET; ele esconde DSA/compliance
DSA                                         | GET `dsa_beneficiary` e `dsa_payor`; copiar string exata da API
Campaign category                          | Confirmar `FINANCIAL_PRODUCTS_SERVICES` e `special_ad_category_country`
Adset parity                               | Diff `optimization_goal`, `billing_event`, `destination_type`, `promoted_object`, `targeting`, `attribution_spec`
Campos graváveis ausentes                  | Listar `SÓ NA SOURCE` e `VALOR DIFERENTE` antes de escrever
Campos derivados                           | Não enviar `configured_status`, `effective_status`, `source_adset_id`
Execução                                   | Criar um objeto por vez, PAUSED, validar GET e parar no checkpoint
Falha `100/1487202`                        | Tratar como campo/regra compliance ausente; não isolar cegamente campos um por um
```

Detalhe de sessão DSA/1487202: `references/eu-dsa-adset-diagnostic-2026-06-19.md`.
Detalhe source mirror EU/financeiro, page permission e attribution blockers: `references/eu-finserv-source-mirror-and-adset-errors-2026-06-19.md`.

## Source mirror obrigatório antes de writes EU/financeiro

Antes de qualquer `POST /campaigns`, `/adsets`, `/adcreatives` ou `/ads` em campanhas EU/financeiro, rodar o mirror read-only:

```bash
/root/mgs-agent/scripts/ares-meta-source-mirror.py \
  --source-campaign-id <campaign_id> \
  --source-adset-id <adset_1> \
  --source-adset-id <adset_2> \
  --source-ad-id <winner_1> \
  --source-ad-id <winner_2> \
  --source-ad-id <winner_3> \
  --ads-count 3 \
  --daily-budget-usd 25
```

Regra aprendida com correção do Rodolfo: não testar payload mínimo nem reportar “não achei” campos sem antes fazer GET explícito e diff source-vs-payload. Default GET da Meta esconde campos de compliance.

Campos de compliance que devem ser confirmados por API e copiados exatamente no adset quando existirem:

```text
dsa_beneficiary
dsa_payor
regional_regulated_categories
special_ad_categories / special_ad_category_country
```

Para OpenzedFinanzas EU/Spain, valores observados nos adsets Patricia/Elena:

```json
{
  "dsa_beneficiary": "Openzed",
  "dsa_payor": "Openzed",
  "regional_regulated_categories": ["SPAIN_FINSERV", "VOLUNTARY_VERIFICATION"]
}
```

Pitfalls validados:
- `code=100/subcode=1487202` pode esconder erro de permissão de Página. Capturar raw HTTP body/headers; o corpo completo pode conter `error_user_title: El permiso de la página es insuficiente...`. Nesse caso, parar: precisa acesso de criação de anúncios na Página, não mais tentativa de campo.
- `code=100/subcode=1885501` em Elena indicou janela de atribuição inválida **no contexto novo incompleto**. Não trocar automaticamente para `(1,0)` quando a source UI/API mostra `7-day click + 1-day view`; isso é sinal de que a campanha/adset novo ainda não espelha o contexto da source. Primeiro corrigir paridade de campaign/adset (COST_CAP, bid_amount, `smart_promotion_type`, pacing, DSA/regional, promoted_object, targeting) e só mudar attribution se Rodolfo aprovar conscientemente um replacement não-fiel.
- Sempre deletar/verificar campaign parcial quando o adset falha e a campaign não será reutilizada no próximo checkpoint.

## Script canônico

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py \
  --account-id 1356770869843984 \
  --operation-id OpenzedFinanzas-CC-ES \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25
```

Dry-run:

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py --dry-run
```

## Criativos vencedores do dry-run inicial

Dry-run real salvo em `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-dry-run-20260618T035853Z.json`:

```text
Source campaign                                 | Source ad ID        | Creative ID       | Spend | MO | CPMO
------------------------------------------------|---------------------|-------------------|-------|----|------
Patricia Flores - US - ESP - (pg_22069) - 4     | 120248290564590604  | 1878134753167706  | 9.36  | 7  | 1.34
Patricia Flores - US - ESP - (pg_22069) - 1     | 120248290297210604  | 1018755007258886  |107.96 |70  | 1.54
Patricia Flores - US - ESP - (pg_22069) - 3     | 120248290564610604  | 1829542905087157  |101.34 |58  | 1.75
```

## Tentativa real 2026-06-18

A tentativa controlada de clone foi executada com criação PAUSED e budget `daily_budget=2500` (USD 25). Resultado:

```text
Etapa                     | Resultado
--------------------------|--------------------------------------------------
Campanha PAUSED           | criada com sucesso em tentativas parciais
Adsets PAUSED             | criados após ajustar special_ad_category_country=ES e attribution 1d click
Adcreative novo           | Meta rejeitou recriação DCO por link messenger_doc como externo
Ad com creative existente | Meta bloqueou por pending account authentication
Bloqueio final            | code=31, subcode=3858385, Ads Manager exige autenticar conta
Limpeza                   | campanhas parciais foram marcadas DELETED e verificadas via GET
```

Audits:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T035944Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T040046Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T040141Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889706550604.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889834980604.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889873410604.json
```

Nova tentativa com até 3 alternativas em `/root/mgs-agent/scripts/ares-meta-clone-troubleshoot-3alts.py` confirmou o bloqueio:

```text
Alternativa | Método                                      | Resultado
------------|---------------------------------------------|-------------------------------
1           | build exato: campaign + adsets + 3 ads       | bloqueou em create_ad code=31/subcode=3858385
2           | Meta native campaign copies endpoint         | bloqueou code=100/subcode=1885194
3           | campaign+adset manual + ad copies endpoint   | bloqueou ad copy code=100/subcode=3858504
```

Auditoria: `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-troubleshoot-3alts-20260618T041137Z.json`.
Campanhas parciais criadas nas alternativas 1 e 3 foram marcadas `DELETED` e verificadas via GET. Não tentar novas variações até a conta ser autenticada no Ads Manager ou Rodolfo confirmar outro usuário/token/ad account.

Próximo clone real depende de Rodolfo/usuário autenticando a conta no Ads Manager para remover o pending action.

## Prioridade operacional: separar “replacement Ares” de “clone fiel”

Correção explícita do Rodolfo em 2026-06-19: não misturar a lógica de gestão/performance com a mecânica de construção da campanha. A palavra “clone” foi usada em dois sentidos e isso causou erro operacional.

```text
Caminho                         | Significado
--------------------------------|------------------------------------------------------------
Replacement Ares 1x3             | campanha nova padronizada: 1 adset, 3 ads, budget USD 25
Clone fiel / source mirror       | espelhar a estrutura real da campanha source: adsets/ads/campos
```

Se a conta estiver sob gestão 100% Ares, o padrão oficial deve ser **Replacement Ares 1x3**; campanhas manuais existentes servem como fonte de performance/assets/aprendizado, não como estrutura obrigatória. Se Rodolfo pedir clone fiel de uma campanha manual, então a source decide quantidade de adsets, attribution, DSA, regional compliance, targeting e demais campos graváveis.

Referência detalhada: `references/ares-standard-vs-source-mirror-2026-06-19.md`.

Referência Elena UI→API/source mirror: `references/elena-ui-api-source-mirror-2026-06-19.md`.

Referência do probe pragmático que destravou campaign + primeiro adset da Elena e isolou o bloqueio final em `POST /ads`: `references/elena-pragmatic-resolution-2026-06-19.md`.

Referência BM/Page vs bloqueio API em `POST /ads` mesmo com Marcos tendo Manage campaigns na ad account e controle absoluto da Página Elena: `references/bm-permissions-vs-api-ad-auth-block-2026-06-19.md`.

Referência final do token novo + clone full Elena bem-sucedido: `references/elena-full-clone-token2-success-2026-06-19.md`.

### Status validado em 2026-06-19 — clone e ativação funcionam

O bloqueio `code=31/subcode=3858385` em `POST /ads` foi resolvido após Rodolfo gerar novo token incluindo escopos de Página/Messenger:

```text
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

Com o token novo, Ares validou:

```text
Operação                              | Status
--------------------------------------|------------------------------------------------
Criar campaign                        | OK
Criar adset                           | OK
Criar 3 ads                           | OK
Ativar campaign/adset/ads             | OK
Pausar campaign                       | OK
Clone full Elena 2 adsets / 6 ads     | OK
```

Objetos principais criados:

```text
Teste 1x3 TOKEN2 campaign             | 120248959079740604
Clone full Elena campaign             | 120248959247790604
```

O clone full da source `120248940367540604` criou 2 adsets e 6 ads, PAUSED, com budget source USD 100/dia porque o pedido foi “do jeitinho que ela é”. A única divergência operacional validada: source Elena usa `7-day click + 1-day view`, mas criação nova retornou `1885501`; clone aceito com `1-day click`. Regra: tentar primeiro o valor da source em clone fiel; se Meta rejeitar com `1885501`, usar `CLICK_THROUGH 1` e reportar a divergência.

Correção anterior do Rodolfo: quando o pedido for clone fiel, priorizar **clone/source mirror** como os buyers/Ads Manager fazem, não criação from-zero genérica. Criação from-zero pode falhar para este usuário/token e só ser viável em outro contexto de System User; **não usar criação do zero genérica como prova, teste principal ou resposta operacional quando Rodolfo pedir clone fiel**.

Regra de interpretação do escopo:
- Campanhas `ACTIVE` e `PAUSED/OFF` são fontes válidas de clone. `PAUSED` não é deletada.
- Ares deve conseguir listar e analisar todas as campanhas visíveis da conta, ligadas ou desligadas, e escolher a melhor base conforme as regras de performance quando o fluxo estiver estabilizado.
- Para testes iniciais de clone, se Rodolfo disser "qualquer uma da conta", tentar qualquer campanha viável; basta uma funcionar para desbloquear o método e depois voltar ao ranking/regras.
- Só considerar sucesso se o clone/copy trouxer estrutura utilizável com adsets/ads. Uma cópia rasa de campaign sem adsets/ads é artefato parcial e deve ser deletada/verificada.

Fluxo preferido para nova tentativa:

```text
Ordem | Caminho
------|------------------------------------------------------------
1     | Validar token e listar campanhas/adsets/ads incluindo OFF/PAUSED
2     | Tentar Meta native copy endpoints (`/copies`) preservando PAUSED
3     | Se campaign `deep_copy` falhar em uma source, testar outras campaigns da conta
4     | Se campaign rasa copiar só shell, não chamar de sucesso; testar adset/ad copy nativo
5     | Se copy falhar por `standard_enhancements`, suprimir/normalizar creative features
6     | Só usar rebuild manual de creative/ad como diagnóstico separado, nunca como substituto do clone pedido
7     | Validar GET e deletar qualquer cópia rasa/parcial sem adsets/ads esperados
```

Pitfalls validados:
- `/<campaign_id>/copies` sem `deep_copy` cria só uma campanha vazia. Não considerar isso clone bem-sucedido; verificar contagem de adsets/ads antes de manter.
- Em 2026-06-18, `/<campaign_id>/copies deep_copy=true` falhou nas 20 campaigns visíveis com `code=100/subcode=1885194`; adset copy raso/deep também falhou em Elena com `1885501`/`1885194`. Isso não significa que campanhas estão invisíveis; significa que o payload público simples ainda não reproduz o clone do Ads Manager/buyers.
- Se o usuário corrigir "não é para criar do zero", parar de misturar fallback from-zero no relatório e responder apenas sobre clone/copy nativo.

Detalhes de sessão e erros Meta de copy nativo:
- `references/native-copy-standard-enhancements-2026-06-18.md`
- `references/native-copy-all-campaigns-probe-2026-06-18.md`

## Correção aprendida com playbook externo de clone

Rodolfo trouxe um playbook de outro agente para criação/clonagem Meta. A diferença crítica contra a primeira implementação local é:

```text
Rota antiga local                | Rota correta para Messenger/replacement
---------------------------------|------------------------------------------------
Reaproveitar object_story_spec bruto | Não usar object_story_spec bruto de campanha antiga
Reaproveitar asset_feed_spec bruto   | Recriar creative a partir de video_id ou image_hash
Fallback com creative_id legado      | Evitar como rota padrão, especialmente cross-page
Graph v20.0                          | Preferir v25.0 para o fluxo de criação se validado
Recriar messenger_doc como link      | Não usar messenger_doc como destino externo
```

Para `clone-source` na mesma página:
1. Ler ads ativos da source.
2. Extrair `video_id` para vídeos ou `image_hash` para imagens.
3. Criar novos adcreatives com `object_story_spec` mínimo contendo `page_id` e asset (`video_data.video_id` ou `link_data.image_hash` quando aplicável), mais `degrees_of_freedom_spec` e `page_welcome_message` seguro.
4. Em Messenger, `page_welcome_message` deve usar `is_user_editing=true` e não enviar `template_id` nem `template_version`.
5. Não enviar `standard_enhancements`.
6. Exigir 3 ads utilizáveis; se criar menos de 3, arquivar/deletar a campanha parcial.

Read-only em 2026-06-18 confirmou que os 3 creatives winners atuais possuem `asset_feed_spec.videos` com `video_id` disponível, então há insumo para trocar o script para uma rota baseada em `video_id`, não em `messenger_doc`/creative bruto. Auditoria: `/root/mgs-agent/data/ares/meta-ads/audit/clone/creative-asset-inspect-readonly.json`.

Tentativa controlada posterior criou com sucesso campanha PAUSED, adset PAUSED e adcreative novo usando `video_id + image_url` de thumbnail, sem `messenger_doc`. O bloqueio remanescente ficou no `POST /ads`: `code=31/subcode=3858385`. Ou seja, a rota de criativo foi corrigida; a camada de criação do ad via API continua bloqueada para o token/app atual. Auditoria principal: `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-videoid-failed-20260618T044855Z.json`. Campanha parcial `120248892823990604` foi marcada `DELETED` e verificada via GET.

## Diagnóstico token/app, página alternativa e camada `POST /ads`

Quando Rodolfo trocar VPS/IP, renovar token, pedir "teste novamente" ou perguntar se outra página/campanha da conta pode ser usada, não assumir que a camada bloqueada é a mesma da tentativa anterior. Rodar uma validação em camadas:

```text
Camada                 | Decisão operacional
-----------------------|------------------------------------------------------------
Token 1Password         | Reportar só item/campo/len; nunca imprimir valor
Mapa páginas/campanhas  | Listar campaigns/adsets/page_id antes de concluir bloqueio global
GET source campaign     | Se falhar, parar antes de writes
Create campaign/adset   | Só se GET source estiver OK; página alternativa pode passar adset
Create creative         | Validar `video_id`/`image_hash`; testar sem IG se houver erro de Instagram asset
POST /ads               | Isolar final layer; code=31/subcode=3858385 exige autenticação Ads Manager
Cleanup                 | Deletar/verificar campanha temporária se qualquer write ocorreu
```

Interpretação validada:
- `code=31/subcode=3858385` em `POST /ads`: a rota de campanha/adset/creative pode estar correta; a trava está na criação/modificação de anúncio pela conta/app/usuário.
- `code=190` com `Error validating application. Application has been deleted.` já no primeiro GET: token/app inválido ou app deletado. Corrigir app/token antes de novo clone; mudança de VPS/IP não resolve essa camada.
- `code=100/subcode=1487202` em `create_adset` com título de permissão de Página insuficiente: token/user não tem acesso para anunciar naquela Página; testar outra página da conta pode isolar se o bloqueio é local à Página.
- `code=200/subcode=1815199` em `create_adcreative` com erro de Instagram asset: retestar com `--omit-instagram-user-id` para criar creative page-only e separar erro de IG do bloqueio final.
- Se o clone completo estiver lento por backoff/rate-limit de crons Meta concorrentes, usar um probe focado sem backoff longo para separar token/app vs `POST /ads`, mas manter cleanup/verificação obrigatórios.

Detalhe de sessão e receita do probe: `references/token-app-validation-and-post-ads-retest-2026-06-18.md`.
Detalhe do reteste em outra página e flag `--omit-instagram-user-id`: `references/retest-other-page-and-omit-instagram-2026-06-18.md`.
Detalhe consolidado do token OK + página Elena + no-IG + bloqueio final em `POST /ads`: `references/page-permission-noig-post-ads-block-2026-06-18.md`.

## Comunicação com Rodolfo em troubleshooting Meta

Se Rodolfo disser que não entendeu por estar técnico demais, reduzir imediatamente para linguagem operacional:

```text
Pergunta executiva                 | Resposta curta esperada
-----------------------------------|------------------------------------------------------------
O token funciona?                   | Sim/não, com /me e conta como evidência
O que a Meta deixou fazer?          | Campanha/adset/creative/ad em passos simples
Onde travou?                        | Nome humano da trava, não só código/subcode
O que precisa fazer agora?          | Ação humana específica no Ads Manager ou permissão da Página
```

Use códigos (`31/3858385`, `1487202`, `1815199`, `190`) como evidência curta em tabela depois da explicação simples. Não liderar com `object_story_spec`, `standard_enhancements`, Graph payloads ou async session salvo se Rodolfo pedir detalhe técnico.

## Pitfalls

- Nunca aplicar “payload padrão Ares” e chamar de clone fiel. Se a source tem 2 adsets/6 ads, criar 1 adset/3 ads é **replacement Ares 1x3**, não clone estrutural. Declare o modo antes de escrever.
- Não trocar campos da source por sugestão de erro genérico da Meta quando o objetivo declarado for clone fiel. Ex.: Elena mostrava `7-day click, 1-day view` na UI/API; a resposta `1885501` sugerindo `(1,0)` inicialmente indica contexto de criação incompleto, não autorização automática para alterar a attribution da source.
- Exceção de diagnóstico pragmático: se Rodolfo pedir para “resolver não importa como” ou aceitar um teste não-fiel só para destravar a camada API, `attribution_spec=[CLICK_THROUGH 1]` passou para o primeiro adset Elena com DSA/regional/COST_CAP/bid_amount corretos. Rotular isso como workaround diagnóstico, não clone fiel nem padrão permanente.
- Em conta EU/financeiro, fazer GET explícito de compliance antes de POST: `dsa_beneficiary`, `dsa_payor`, `regional_regulated_categories`, `special_ad_categories`, `special_ad_category_country`. Defaults da API escondem campos.
- Se a Meta retornar erro de permissão de página (`El permiso de la página es insuficiente para publicar anuncios`), parar. Não resolver mudando payload.
- Se uma campaign criada voltar `start_time=1970`, tratar como campanha mãe malformada/suspeita antes de debugar adset.
- `code=31/subcode=3858385` pode aparecer como mensagem genérica de autenticação na API mesmo quando Ads Manager manual não mostra checkpoint; antes de concluir checkpoint humano, testar se o payload está usando a rota correta (`video_id`/`image_hash`) e Graph version compatível.
- `code=190` com "Application has been deleted" não é problema de payload de clone: é token/app inválido. Não criar campanhas temporárias quando o GET source já falha.
- A campanha original tem budget USD 100; replacement precisa forçar USD 25, nunca copiar o budget original.
- Criativos Advantage/DCO/Messenger podem rejeitar recriação de `asset_feed_spec` bruto por `messenger_doc`; não insistir nesse caminho.
- Não usar `creative_id` de outra página como rota padrão. Para criativo de outra página, reconstruir por Drive/asset autorizado.
- Não ativar a campanha no ato do clone. Começar PAUSED e validar estrutura, salvo autorização explícita para ACTIVE.
- Não deletar/arquivar loser antes de clone e validação.
- Não imprimir token Meta nem payload com token em logs.
