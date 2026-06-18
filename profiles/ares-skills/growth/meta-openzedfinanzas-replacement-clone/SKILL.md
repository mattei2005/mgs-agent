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
2. Start time deve ser o dia seguinte às `01:00` no timezone da conta.
3. Campaign daily budget nunca pode passar de `USD 25` inicialmente (`daily_budget=2500` cents).
4. Clonar estrutura do zero: campanha nova, adset novo, criativo/ad novo.
5. Selecionar exatamente 3 criativos vencedores da conta inteira, não só da campanha/página.
6. Ranking inicial de criativo vencedor: menor CPMO nos últimos 3 dias, com `spend >= USD 5` e `MO >= 2`.
7. Clone usa a mesma página/promoted object da loser, mas os criativos podem vir de outra campanha/página se forem vencedores da conta.
8. Depois do clone validado, loser deve ser deletada se a API permitir; se não permitir delete, arquivar/pausar.
9. Antes de reportar sucesso, validar com GET: campanha criada, status, budget, adsets e exatamente 3 ads.
10. Salvar audit em `/root/mgs-agent/data/ares/meta-ads/audit/clone/`.

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

## Pitfalls

- `code=31/subcode=3858385` pode aparecer como mensagem genérica de autenticação na API mesmo quando Ads Manager manual não mostra checkpoint; antes de concluir checkpoint humano, testar se o payload está usando a rota correta (`video_id`/`image_hash`) e Graph version compatível.
- `code=190` com "Application has been deleted" não é problema de payload de clone: é token/app inválido. Não criar campanhas temporárias quando o GET source já falha.
- A campanha original tem budget USD 100; replacement precisa forçar USD 25, nunca copiar o budget original.
- Criativos Advantage/DCO/Messenger podem rejeitar recriação de `asset_feed_spec` bruto por `messenger_doc`; não insistir nesse caminho.
- Não usar `creative_id` de outra página como rota padrão. Para criativo de outra página, reconstruir por Drive/asset autorizado.
- Não ativar a campanha no ato do clone. Começar PAUSED e validar estrutura, salvo autorização explícita para ACTIVE.
- Não deletar/arquivar loser antes de clone e validação.
- Não imprimir token Meta nem payload com token em logs.
