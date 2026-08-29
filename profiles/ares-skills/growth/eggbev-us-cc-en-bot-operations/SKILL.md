---
name: eggbev-us-cc-en-bot-operations
description: "Use em Campaign Ops BOT/Messenger da Eggbev US-CC-EN."
version: 0.8.0-draft
author: Ares
license: internal
metadata:
  hermes:
    tags: [eggbev, usa, credit-cards, english, meta-ads, messenger, bot, campaign-ops]
---

# Eggbev US-CC-EN BOT Operations

Skill específica da operação Meta Ads Eggbev USA, vertical Credit Cards, idioma inglês, estratégia BOT/Messenger.

## When to Use

Use quando Rodolfo ou Nicolas pedir revisão de regras, análise, relatório, campanha, criativo, cron ou mudança Meta Ads da operação Eggbev US-CC-EN BOT. Não usar para tráfego direto nem para configurar internamente ChatPion/DigitalTrChat sem escopo explícito.

## Estado atual

```text
Status do contrato       runners ROAS/Diário construídos; aguardando dados reconciliados e dry-run com entrega
Operation ID             Eggbev-US-CC-EN-BOT
Conta Meta               act_1034081997659047; alias Eggbev-US-CC-EN-01-G006
Gestão                    Rodolfo Mattei + Nicolas
Write Meta                ROAS disabled; lead guardrail scoped write enabled
Crons Eggbev              somente guardrail de leads; nenhum cron ROAS/Diário
Regra nativa              ADS ZERO RESULTS segue ativa; Nicolas autorizou desativá-la somente na futura ativação
Herança tráfego direto    proibida sem revisão explícita
Herança operação anterior proibida
```

O estado vivo está nos arquivos canônicos de operação e conta em `data/ares/meta-ads/`. IDs técnicos completos e referência de credencial ficam nesses arquivos/audits, nunca no relatório humano.

## Threads fixas

```text
Tipo              Thread ID
----------------  -------------------
Regras             1543280854024060999
Intraday           1541578606076231750
Diário             1541578596253175858
Criar campanhas    1541578556037927053
Clonar campanhas   1543333373945053184
Limite de Leads    1543312825890381865
```

Nunca criar uma thread substituta quando uma dessas rotas se aplicar. Toda thread nova do canal deve incluir Zeus e Nicolas conforme a política Discord vigente.

Por instrução explícita de Nicolas em 29/08/2026, a rota canônica de **Regras** passou a ser a thread atual `1543280854024060999`. A antiga `Eggbev-US-CC-EN Regras` (`1541578622106865815`) fica supersedida e não recebe novas regras ativas.

## Escopo Ares

Ares gerencia a camada de aquisição e Campaign Ops ao redor do BOT:

- arquitetura de campanha Meta;
- contas, campanhas, adsets, ads e criativos;
- naming, inventário e reconciliação Drive × Meta;
- relatórios Intraday e Diário;
- recomendações, guardrails, custo, performance e ROI quando as fontes forem definidas;
- crons determinísticos somente após contrato e aprovação.

Configuração interna de ChatPion, DigitalTrChat, quiz, SMS Funnel, WordPress ou pixel/CAPI crítico não entra automaticamente neste escopo. Qualquer uma dessas camadas exige pedido explícito de Rodolfo e a rota técnica correspondente.

## Separação obrigatória de tráfego direto

Não copiar automaticamente para BOT/Messenger:

- objetivo e optimization goal;
- destination/conversion location;
- estrutura CBO/ABO;
- bid strategy e cost cap;
- público, placements e attribution;
- evento de conversão;
- fórmula de resultado/custo;
- thresholds de pausa/reativação;
- horários Intraday/Diário;
- regras de criação, ativação, replacement e escala;
- naming e UTMs.

Somente guardrails genéricos de segurança, idempotência, autorização e readback podem ser compartilhados após revisão de compatibilidade.

## Pendências residuais antes do canário

O contrato de estrutura, horários, threshold, guardrail, publicação e reporting já foi consolidado nas seções seguintes. Permanecem pendentes somente as camadas dependentes de evidência ou decisão ainda ausente:

1. Smart Bidding: mapping inequívoco da conta 01, atraso e fórmulas Eggbev de ROI/RPS/receita líquida.
2. Engine v3: onboarding da conta Eggbev, media registry pre-stageado e extensão explícita do manifest/executor para `clone_page_switch`.
3. `clone_page_switch`: validar no canário os campos exatos do JSON Messenger e a troca da Page/identidade no creative; a regra operacional já está aprovada.
4. ROAS: comando aprovado de alteração intraday e eventual fórmula de recomendação de threshold.
5. Diário com volume: layout final card único versus card + tabela por campanha.
6. Canário live: validar payload, serving, métricas e readbacks com uma campanha aprovada.
7. Regra nativa `ADS ON 1.1` em `HAS_ISSUES`: manter, desativar ou remover exige decisão específica.

Cada pendência bloqueia somente a ação dependente; não reabre regras já aprovadas.

## Contrato confirmado em blocos — criação, ciclos e reporting

Fonte canônica: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json` v0.2-draft. Este resumo não substitui o JSON vivo.

### Criação de campanha

```text
Campaign  Auction | Sales | CBO | Highest volume | Standard | Financial products/services US
Ad set   AdG1 | Messenger | next day 00:00 America/New_York | ongoing | US 18+ All
Ads      1x1x3 ou 1x1x5 | manual upload | Instagram usa Facebook Page
Pixel    Eggbev-US-CC-EN; mesmo pixel para toda a operação
Payer    DIGITAL TRUST; sempre nesta operação
Budget   variável; confirmar por campanha
Exceção  clone_page_switch = USD 45, somente após o resumo final daquela solicitação ser aprovado
```

Placements são manuais conforme a lista do contrato; nunca converter para Advantage+ Placements. Criativo sempre novo de `CC_US_EN`, após reserva e conciliação Meta × Drive. Se faltar nome individual do ad, página, budget, estrutura, criativo ou copy, perguntar apenas o campo ausente.

O template Messenger é obrigatório. Qualquer mudança de texto, botão, payload ou flags exige versão integral + aprovação de Nicolas. Antes de qualquer publicação, apresentar o resumo final e esperar OK explícito; a instrução atual da campanha vence o print de referência.

### Ciclos ROAS

```text
00:00               reset diário do threshold para 0,40
00:00–06:00         formação de dados; sem corte/reativação
Fase 1              06:00, 08:00, 10:00, 12:00
Corte Fase 1        Spend > USD 2 E Purchase ROAS < threshold
Fase 2              13:00, 14:00, 16:00, 18:00, 20:00, 22:00, 23:00
Corte Fase 2        Purchase ROAS < threshold; sem gate de gasto
Reativação          ad pausado pelo Ares com Purchase ROAS > mesmo threshold
23:00–00:00         sem novo corte/reativação
```

Threshold é simétrico; valor exatamente igual não muda estado. Mudança intraday depende do OK de Nicolas. Purchase ROAS vazio com fonte válida é elegível a corte e aparece `N/D`: na Fase 1 o gate `Spend > USD 2` continua; na Fase 2 não há gate de gasto. Fonte indisponível, atrasada ou irreconciliável gera `no_write + alerta`, não deve ser confundida com métrica individual vazia.

A ação padrão de ROAS é no ad. Se o ciclo deixar zero ads ativos, cortar todos os elegíveis e pausar a campanha; não pausar o ad set. Essa decisão supersede a invariante anterior de nunca pausar campanha. Se um ad pausado pelo Ares recuperar Purchase ROAS acima do threshold, reativar automaticamente o ad e a campanha no mesmo ciclo, sempre com pré-leitura e readback pós-write.

### Reporting

- Intraday: um relatório por ciclo e qualquer atualização sob demanda.
- Núcleo Meta: CPM, Purchase ROAS, custo por resultado/conversa, Results, Budget, Amount spent e CTR.
- Núcleo Smart Bidding solicitado: Leads/UTM, RPS, ROI drip, performance completa, investimento, receita, receita líquida/estimada e ROI real/estimado.
- Não inventar fórmulas; validar campo, granularidade e atraso na fonte viva.
- Diário aprovado em múltiplos horários, inspirado na distribuição do Crédito para Veículo e adaptado ao BOT: 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 e 22:00 ET. Não automatizar antes de apresentar o plano final e obter OK explícito de Nicolas.
- Thread Intraday fixa: `Eggbev-US-CC-EN Corte e ROAS` (`1541578606076231750`), nome confirmado por readback.
- Padrão das rotas funcionais: prefixo `Eggbev-US-CC-EN` antes da função. Exceção aprovada por Nicolas: Regras usa a thread atual `1543280854024060999`; a antiga thread de Regras foi supersedida.

## Guardrail aprovado — limite de leads por página

Nicolas aprovou o guardrail específico da conta `Eggbev-US-CC-EN-01-G006`:

```text
Fonte                 Smart Bidding /campaigns/Messenger, publisher Eggbev
Métrica de ação        LEADS (não LEADS_TOTAL)
Operador               estritamente > 5000
Chave primária         UTM_CAMPAIGN exato no padrão pg_XXXXX
Confirmação identidade FB_PAGE_ID da SB = page_id do creative Meta
Escopo Meta            campanha efetivamente ACTIVE com ad efetivamente ACTIVE
Ação                   pausar a campanha inteira; sem budget/delete
Reativação             nunca automática
Frequência aprovada    08:00 e 20:00, America/New_York
Relatório automático   silencioso sem ação; publicar quando houver pausa ou erro
Relatório sob pedido   todas as páginas ativas reconciliadas, com LEADS e proximidade por emoji
```

Este guardrail é exceção explícita à regra de cortes por ROAS: ROAS atua em anúncios; limite de leads atua na campanha inteira. Mapeamento ausente, duplicado ou divergente é `fail_closed_no_write`. Antes do POST, ler o estado real; depois do POST, fazer GET/readback. POST falho é reconciliado por GET e nunca repetido às cegas.

O alerta obrigatório inclui página, UTM, LEADS, estado `RESTRICTED_UNTIL` da Smart Bidding, campanhas pausadas, horário ET, snapshot Meta de hoje e contagem de readbacks. `RESTRICTED_UNTIL` é estado da Smart Bidding e não deve ser descrito como prova independente de uma restrição DTR `#2022`.

Runtime:

```text
Thread fixa           Eggbev-US-CC-EN Limite de Leads (`1543312825890381865`)
Runner                 /root/mgs-agent/scripts/ares-eggbev-page-lead-guardrail.py
Wrapper                /root/.hermes/profiles/ares/scripts/eggbev-page-lead-guardrail.sh
Modo                   dry-run e controlled-write preflight validados
Cron                   `0 8,20 * * *`, no_agent=true, deliver=local, enabled/scheduled
Estado do scheduler    processo Ares ativo, mas cron tool ainda informa gateway_running=false; automação não é considerada provada até readback de um tick programado após a auditoria
```

Quando Nicolas pedir relatório, executar leitura real e mostrar todas as páginas exatamente reconciliadas com campanhas e anúncios ativos. Usar **proximidade ao limite**, sem chamar de previsão estatística:

```text
🟢 0–3.999 LEADS      abaixo de 4k
🟡 4.000–4.499 LEADS  atenção
🟠 4.500–5.000 LEADS  muito próxima
🔴 >5.000 LEADS       pausar campanha e reportar com readback
```

A proximidade percentual é `LEADS / 5000`. O check automático permanece silencioso quando não há ação; relatório de status completo é enviado sob pedido do gestor.

## Thread dedicada — Clonar campanhas

Thread fixa: `Eggbev-US-CC-EN Clonar Campanhas` (`1543333373945053184`). Criada por pedido explícito de Nicolas, com Nicolas, Zeus e Rodolfo confirmados por readback e três mensagens de contrato confirmadas.

Escopo exclusivo de clonagem; criação do zero permanece em `Eggbev-US-CC-EN Criar Campanhas`. Executor obrigatório: `meta-campaign-engine-v3`. Modos não intercambiáveis:

- `pure_clone`: preserva estrutura, público, budget, copy e mídia; reescreve próximo sequencial, naming e tracking; sufixo `COPY C{fonte}`;
- `clone_prestaged`: preserva lineage/estrutura e usa criativos novos aprovados, reconciliados e pre-stageados;
- `clone_page_switch`: duplica integralmente a fonte, preservando estrutura, público, placements, estratégia, copy e mídia, mas muda a Facebook Page para a página-alvo, reescreve próximo sequencial, nome, `pg_XXXXX`, links/UTMs e o JSON Messenger. A página é indicada por Nicolas; quando Nicolas delegar a escolha, usar a página elegível em entrega com menor `LEADS` no Messenger Pages da Smart Bidding, após match único `UTM_CAMPAIGN + FB_PAGE_ID`. Empate, fonte stale ou mapping inválido bloqueia a escolha automática. Neste modo, budget = USD 45, início = dia seguinte 00:00 `America/New_York` e campanha/ad set/todos os ads ficam `ACTIVE` para o início aprovado.

Antes do primeiro plan/write Eggbev, cadastrar a conta no v3 e validar manifest. O Engine v3 atual não aceita `clone_page_switch`; a regra está aprovada no contrato, mas a execução permanece bloqueada até uma extensão explícita do manifest/executor com testes. A thread deve receber campanha-fonte, modo, página/UTM, budget, início ET, estrutura 1×1×3 ou 1×1×5 e os campos específicos do modo. Em `clone_page_switch`, mostrar também evidência `LEADS`, Page/`pg_XXXXX`, nome final, links/UTMs, JSON Messenger integral, budget USD 45, início 00:00 ET e todos os status. Mostrar resumo final e esperar OK explícito de Nicolas; nunca publicar direto. Não existe cron de clonagem.

## Auditoria pré-simulação — 2026-08-29

Todas as seis rotas fixas foram atualizadas com regras, riscos e testes; a thread de status também foi atualizada e duas threads históricas receberam aviso de supersessão mantendo o estado arquivado. Readback confirmou 16/16 mensagens e Nicolas, Zeus e Rodolfo em todos os nove alvos da API. Um HTTP 429 ocorreu após efeito parcial: o recovery fez GET de todas as threads, pulou membros/posts já confirmados e publicou apenas as camadas ausentes; zero duplicatas no readback final.

Bloqueios reais antes do canário:

1. observadores do scheduler discordam: processo Ares ativo, cron tool com `gateway_running=false`; confirmar um tick programado antes de confiar na automação de LEADS;
2. Smart Bidding sem conta 01 no report;
3. `ADS ZERO RESULTS` ainda ENABLED; desativar somente no gate futuro já autorizado;
4. `ADS ON 1.1` em `HAS_ISSUES`, sem decisão de remoção/desativação;
5. conta Eggbev ausente do Engine v3 e do media registry;
6. zero campanhas/ads ativos impede validação live de métricas/serving/readback;
7. ROI/RPS/receita líquida e recomendação de threshold sem fórmula aprovada;
8. comando de mudança intraday do threshold ainda não implementado.

Decisões de clonagem atualizadas:

- `pure_clone` e `clone_page_switch` são exceções aprovadas que preservam mídia/copy; campanhas novas e `clone_prestaged` continuam exigindo criativos novos;
- `pure_clone` usa o sufixo `COPY C{fonte}`; `clone_page_switch` usa o naming canônico com próximo sequencial, página-alvo e novo `pg_XXXXX`;
- `clone_page_switch` usa USD 45, próximo dia 00:00 ET e campanha/ad set/ads `ACTIVE` para o início aprovado;
- permanecem pendentes somente o suporte do v3, os campos exatos de JSON/Page no payload e o canário live;
- layout Diário com volume continua pendente: card único ou card + tabela por campanha.

Ordem de testes: fixtures ROAS → fixtures LEADS → fórmulas/layout Diário → onboarding v3 → validate/plan criação → validate/plan clone → campanha canário aprovada → API×Ads Manager×Smart Bidding → dry-run apresentado → controlled-write/readback → crons.

## Runtime ROAS e reporting construído

Autorização de Nicolas: construir runners e testes sem cron, sem postagem e sem write Meta. Readback atual:

```text
Módulo comum            /root/mgs-agent/scripts/ares-eggbev-roas-common.py
Corte e ROAS            /root/mgs-agent/scripts/ares-eggbev-roas-cycle.py
Diário/sob demanda      /root/mgs-agent/scripts/ares-eggbev-daily-report.py
Testes                  tests/test_eggbev_roas_automation.py
Testes aprovados        47 incluindo regressões do guardrail, rollover de proveniência e contrato clone_page_switch
Write ROAS              false
Post Diário             false
Cron ROAS/Diário        inexistente
```

O runner controla proveniência de ads/campanhas pausados pelo Ares, nunca reativa pausa manual ou do guardrail de leads, não altera ad set e exige pré-leitura + readback. Às 00:00 o reset local para `0,40` independe das fontes e não faz write Meta. Em ciclo de ação, Smart Bidding ausente/irreconciliável ou `ADS ZERO RESULTS` ativa bloqueia writes. Métricas Smart Bidding indisponíveis aparecem `N/D`, nunca zero inventado.

Na leitura real da construção, a conta Meta estava ativa em USD/ET, mas sem campanha/ad/insight; Smart Bidding só expôs a conta 03 e não a conta alvo 01. Portanto, o live dry-run com entrega permanece pendente. Nicolas autorizou desativar `ADS ZERO RESULTS` somente no futuro gate de ativação, com readback exato antes/depois.

## Auditoria ponta a ponta — 2026-08-29

Estado comprovado: conta Meta ativa em USD/ET, zero campanhas/ads ativos, zero spend; Fase 1 e Fase 2 executadas em dry-run; Diário live read-only e relatório de LEADS executados; 47 testes aprovados. Smart Bidding continua sem a conta 01 e `ADS ZERO RESULTS` continua ativa, então ROAS write permanece fail-closed.

Furo corrigido: o reset de 00:00 apagava `paused_ads`/`paused_campaigns` e impossibilitava recuperação em outro dia. O rollover agora reseta threshold/campos diários e preserva a proveniência Ares até reativação ou reconciliação explícita.

Gaps que bloqueiam produção:

1. conta/operação Eggbev ausente do Engine v3;
2. criação e os três clones sem manifest/runner Eggbev;
3. `clone_page_switch` ausente do schema/executor, sem seletor de página nem transformer JSON/Page;
4. Smart Bidding sem conta 01;
5. sem watcher de primeira impressão/gasto;
6. conflito nativo `ADS ZERO RESULTS`;
7. scheduler com observadores divergentes;
8. sem reconciliação durável de intervenção manual versus proveniência Ares;
9. sem política de escala para alta performance;
10. sem precedência/freshness aprovada entre Meta ROAS e Smart Bidding ROI;
11. janela Smart Bidding enviada com limites `Z` precisa ser validada contra o dia ET;
12. runner de LEADS não possui gate de freshness da linha;
13. Phase 2 trata ausência total de insight do ad como `N/D` válido e corta; confirmar esse comportamento para zero-delivery;
14. criação do zero sem política final Eggbev de `PAUSED` técnico versus `ACTIVE` futuro;
15. `ADS ON 1.1` segue `HAS_ISSUES` sem decisão.

O comportamento implementado para performance é: abaixo do threshold corta conforme a fase; igual mantém; acima mantém ou reativa somente objetos pausados pelo Ares; todos os ads cortados pausam a campanha; `LEADS > 5000` pausa a campanha terminalmente. Alta performance não escala budget automaticamente.

## Sequência de implementação

1. Fechar o contrato em conversa com Rodolfo/Nicolas.
2. Atualizar o JSON da operação e versionar regras próprias Eggbev.
3. Fazer análise inicial read-only da conta e calibrar com conferência manual do gestor.
4. Implementar runner específico com manifest, audit e testes.
5. Criar crons em `no_agent=true`, `deliver=local`, primeiro read-only/dry-run.
6. Validar entrega nas threads fixas e reconciliar contagens.
7. Liberar controlled-write ou autonomia somente por decisão explícita e readback.

## Conclusão mínima

Nenhuma ação Meta é considerada concluída sem readback do alvo. Nenhum cron Eggbev é considerado ativo sem readback de `enabled`, `schedule`, `script`, `no_agent` e `deliver`.
