---
name: eggbev-us-cc-en-bot-operations
description: "Use em Campaign Ops BOT/Messenger da Eggbev US-CC-EN."
version: 0.3.0-draft
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
Status do contrato       architecture_review_in_progress
Operation ID             Eggbev-US-CC-EN-BOT
Conta Meta               alias Eggbev-US-CC-EN-01-G006
Gestão                    Rodolfo Mattei + Nicolas
Write Meta                disabled globally; lead guardrail scoped write enabled
Crons Eggbev              guardrail de leads criado; salvo/enabled, aguardando scheduler gateway
Herança tráfego direto    proibida sem revisão explícita
Herança operação anterior proibida
```

O estado vivo está nos arquivos canônicos de operação e conta em `data/ares/meta-ads/`. IDs técnicos completos e referência de credencial ficam nesses arquivos/audits, nunca no relatório humano.

## Threads fixas

```text
Tipo              Thread ID
----------------  -------------------
Regras            1541578622106865815
Intraday          1541578606076231750
Diário            1541578596253175858
Criar campanhas   1541578556037927053
Limite de Leads   1543312825890381865
```

Nunca criar uma thread substituta quando uma dessas rotas se aplicar. Toda thread nova do canal deve incluir Zeus e Nicolas conforme a política Discord vigente.

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

## Contrato pendente — fechar com Rodolfo/Nicolas

Antes de criar runners ou crons, registrar explicitamente:

1. Fluxo real do usuário: anúncio → Messenger → BOT → qual ação final.
2. Objetivo Meta, conversion location, destination e optimization goal.
3. Métrica principal e ordem de fallback: conversa, subscriber, lead, registration, purchase, revenue/ROI.
4. Fonte externa, join key, atraso e fórmula de receita/ROI, se aplicável.
5. Estrutura por campanha: CBO/ABO, quantidade de adsets e ads, públicos e placements.
6. Naming de campanha/adset/ad e data operacional.
7. Budget inicial, nível do budget, moeda e gates de alteração.
8. Bid strategy, cost cap/lowest cost e regras de learning/carência.
9. País/geo, idade, gênero, idioma e exclusões.
10. Criativos: origem, formato, quantidade, rotação, reserva e replacement.
11. Horários e conteúdo do Intraday e do Diário em America/New_York.
12. Quem pode criar, pausar, reativar, editar budget e ativar.
13. Thresholds, persistência, exceções e rollback.
14. Política de campanha nova: sempre PAUSED até gate explícito.

Campos não decididos permanecem `pending_review` e bloqueiam somente a ação dependente.

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
- Thread Intraday fixa: `Corte e ROAS` (`1541578606076231750`), nome confirmado por readback.

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
Thread fixa           Limite de Leads — Eggbev (`1543312825890381865`)
Runner                 /root/mgs-agent/scripts/ares-eggbev-page-lead-guardrail.py
Wrapper                /root/.hermes/profiles/ares/scripts/eggbev-page-lead-guardrail.sh
Modo                   dry-run e controlled-write preflight validados
Cron                   `0 8,20 * * *`, no_agent=true, deliver=local, enabled/scheduled
Estado do scheduler    gateway parado; job salvo, ainda sem disparo automático
```

Quando Nicolas pedir relatório, executar leitura real e mostrar todas as páginas exatamente reconciliadas com campanhas e anúncios ativos. Usar **proximidade ao limite**, sem chamar de previsão estatística:

```text
🟢 0–3.999 LEADS      abaixo de 4k
🟡 4.000–4.499 LEADS  atenção
🟠 4.500–5.000 LEADS  muito próxima
🔴 >5.000 LEADS       pausar campanha e reportar com readback
```

A proximidade percentual é `LEADS / 5000`. O check automático permanece silencioso quando não há ação; relatório de status completo é enviado sob pedido do gestor.

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
