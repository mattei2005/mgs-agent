---
name: chatpion-bot-campaign-operations
description: "Opera campanhas Meta BOT/Messenger por contrato."
version: 0.1.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [chatpion, bot, messenger, meta-ads, campaign-ops]
    related_skills: [meta-campaign-engine-v3, meta-ads-intraday-operations]
---

# ChatPion BOT Campaign Operations

Contrato operacional reutilizável para campanhas Meta com destino Messenger apoiadas por uma estrutura ChatPion/DigitalTrChat. A skill controla Campaign Ops, relatórios e guardrails; não configura usuários, flows, drip, broadcast ou infraestrutura do ChatPion/DigitalTrChat.

## When to Use

Use quando uma operação estiver vinculada à família `chatpion_bot_messenger` e o pedido tratar de:

- regras e readiness da operação;
- criação ou clonagem de campanhas Meta;
- Corte e ROAS;
- Diário e relatórios read-only;
- elegibilidade, restrições e limites de Page;
- alteração durável da estratégia ou de um parâmetro operacional;
- sincronização das projeções canônicas nas threads Discord.

Não use para tráfego direto, quiz/SMS ou configuração do ChatPion/DigitalTrChat.

## Fontes canônicas

- Família: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json`
- Consumidores: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json`
- Operação: caminho `operation_contract` resolvido no registro de consumidores
- Conta: caminho declarado pelo contrato da operação
- Threads: registry e prompts declarados pelo consumidor
- Engine de criação/clone: `meta-campaign-engine-v3`
- Estado real: APIs, runtime, state e audit da operação

Nunca inferir identidade, conta, Page, UTM, budget, threshold, horários, autoridade, cron ou write-enabled a partir desta skill.

## Resolução obrigatória

1. Resolver a thread ou `operation_id` no registro de consumidores.
2. Confirmar que o consumidor está `active`; candidato de onboarding não é operação ativa.
3. Abrir o contrato da família e o contrato exato da operação.
4. Carregar somente a rota pedida: `rules`, `campaign_creation`, `campaign_cloning`, `roas_cycle`, `daily_reporting` ou `page_guardrails`.
5. Consultar conta, runner, state e audit declarados pela operação somente quando a rota exigir.
6. Falhar fechado quando houver binding ausente, ambíguo ou divergente.

## Precedência

```text
pedido atual explícito e autorizado
→ override ativo do contrato da operação
→ mecanismo da família
→ runtime/API para estado vivo
→ histórico somente para auditoria
```

Um parâmetro específico nunca sobe automaticamente para a família. Uma regra familiar nunca copia state, IDs ou autorização entre consumidores.

## Classificação de mudanças

### Mudança de família

É mudança no mecanismo reutilizável: sequência de gates, semântica de uma rota, contrato de readback, recovery, estrutura de aprovação ou política de projeção.

- atualizar skill e contrato da família;
- validar todos os consumidores ativos;
- atualizar as rotas afetadas e a thread Regras de cada consumidor;
- não copiar valores, IDs, schedules ou autoridade entre operações.

### Mudança de operação

É mudança de valor ou exceção: threshold, horário, budget, Page, evento, layout, hold, cron, fonte, autoridade ou capability de uma operação.

- atualizar somente o contrato, runtime e prompts da operação afetada;
- atualizar a rota funcional afetada e a thread Regras desse consumidor;
- não alterar outros consumidores;
- registrar a versão anterior como superseded.

### Regra de extração

Quando uma mudança específica revelar um procedimento reutilizável, promover somente o procedimento para a família. O valor continua no contrato da operação.

## Rotas funcionais

### Regras

Mantém identidade, autoridade, precedência, readiness e mapa das rotas. Não executa trabalho funcional de outra rota.

### Criar campanhas

Fluxo: preflight vivo → Page/UTM → criativos reconciliados → pre-stage → manifest → validate/plan → resumo final → OK do request → Engine v3 → GET/readback. Defaults e campos obrigatórios vêm do contrato da operação.

### Clonar campanhas

O contrato da operação declara os modos suportados. Fonte, colisão de naming, Page, mídia, copy, JSON, budget e start são lidos ao vivo. Schema/plan não prova readiness live; recovery reutiliza request e IDs.

### Corte e ROAS

A família define isolamento, idempotência, proveniência, lane de corte e lane de reativação. Thresholds, comparadores, fases, horários, níveis de write, métricas e budgets são parâmetros obrigatórios da operação.

### Diário

Rota read-only. Período, schedule, fontes, joins, métricas, renderer e postagem automática são definidos por operação. Ausência, staleness ou ambiguidade vira `N/D`, nunca zero inventado.

### Page e limites

A família exige identidade exata, freshness, plano idempotente, fail-closed e readback. Métrica, threshold, Page policy, hold, ações e schedules pertencem à operação.

## Invariantes de execução

- Original e tratado são uma única linhagem criativa.
- Criação e clone usam somente o Campaign Engine v3.
- Mídia nova fica pre-stageada antes do manifest.
- Todo write exige autoridade, pre-read, request persistido e GET/readback.
- Falha após possível efeito parcial inicia recovery readback-first; nunca repetir POST às cegas.
- `ACTIVE` não prova serving; exigir impressão, gasto ou insight real quando a afirmação for de entrega.
- Credenciais, IDs técnicos extensos e billing permanecem fora do texto humano.
- Cron é gatilho, não fonte de estratégia, e segue a política global anti-colisão.
- Configuração do ChatPion/DigitalTrChat permanece fora do escopo padrão do Ares.

## Sincronização das threads

Uma alteração durável aprovada inclui, no mesmo request, a atualização das projeções Discord correspondentes; não exige uma segunda confirmação apenas para refletir a regra já aprovada.

1. Classificar `family` ou `operation`.
2. Persistir e validar primeiro a fonte canônica.
3. Executar `scripts/ares-chatpion-bot-strategy-sync.py --check` para detectar drift.
4. Atualizar prompt/config local da operação.
5. Projetar a mudança na rota funcional afetada e em `rules`.
6. Fazer GET/readback de cada mensagem criada/editada.
7. Persistir IDs/digests e audit da projeção.

A sincronização edita somente a mensagem de projeção controlada pelo Ares. Mensagens humanas, eventos de sistema, rotas e histórico não são deletados. Limpeza destrutiva exige autorização própria e não faz parte do sincronizador.

## Onboarding de nova operação

1. Registrar identidade e ownership sem copiar state da fonte.
2. Validar conta e capabilities em read-only.
3. Criar contrato isolado começando fail-closed.
4. Registrar threads, prompts e membros obrigatórios.
5. Validar relatórios read-only.
6. Preparar criação/clone por manifest.
7. Executar canário autorizado e provar serving.
8. Liberar controlled-write.
9. Liberar automação por último, após inventário de cron.

Nunca herdar implicitamente IDs, budgets, thresholds, Pages, pixels, eventos, JSON, horários, denylist, holds, baselines ou autonomia financeira.

## Verification

- skill e contrato da família não contêm identidade de consumidor;
- consumidor resolve para um único contrato e conjunto de threads;
- cada parâmetro obrigatório tem origem explícita na operação;
- mudança de operação afeta somente um consumidor;
- mudança de família valida todos os consumidores ativos;
- rota funcional e Regras têm projeção com digest/readback;
- existe somente uma versão ativa por chave canônica;
- testes de arquitetura, prompts e operação passam sem Meta write.
