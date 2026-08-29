---
name: eggbev-us-cc-en-bot-operations
description: "Use em Campaign Ops BOT/Messenger da Eggbev US-CC-EN."
version: 0.2.0-draft
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
Write Meta                disabled globally; lead guardrail scoped write approved but runtime blocked
Crons Eggbev              nenhum; guardrail 15 min pending thread ID + scheduler runtime
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
Frequência aprovada    15 minutos, America/New_York
Thread planejada       Limite de Leads — Eggbev, separada da Intraday
```

Este guardrail é exceção explícita à regra de cortes por ROAS: ROAS atua em anúncios; limite de leads atua na campanha inteira. Mapeamento ausente, duplicado ou divergente é `fail_closed_no_write`. Antes do POST, ler o estado real; depois do POST, fazer GET/readback. POST falho é reconciliado por GET e nunca repetido às cegas.

O alerta obrigatório inclui página, UTM, LEADS, estado `RESTRICTED_UNTIL` da Smart Bidding, campanhas pausadas, horário ET, snapshot Meta de hoje e contagem de readbacks. `RESTRICTED_UNTIL` é estado da Smart Bidding e não deve ser descrito como prova independente de uma restrição DTR `#2022`.

Runtime:

```text
Runner   /root/mgs-agent/scripts/ares-eggbev-page-lead-guardrail.py
Wrapper  /root/.hermes/profiles/ares/scripts/eggbev-page-lead-guardrail.sh
Modo     dry-run validado; controlled-write bloqueado até thread ID + runtime
Cron     não criar/ativar sem thread ID real e gateway scheduler operacional
```

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
