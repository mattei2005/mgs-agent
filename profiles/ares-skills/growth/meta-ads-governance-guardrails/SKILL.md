---
name: meta-ads-governance-guardrails
description: "Guardrails e permissionamento para Ares operar Meta Ads: token, budget, rate limit, auditoria, gestores humanos e transição read-only/dry-run/write."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, governance, guardrails, budget, tokens, permissions, mgs]
---

# Meta Ads Governance & Guardrails — Ares/MGS

Status operacional: **não usar como fluxo separado/runtime**. Rodolfo definiu que os guardrails devem fazer parte dos próprios scripts/fluxos de organização e execução na conta. Esta skill fica apenas como referência temporária até ser consolidada em `meta-ads-intraday-operations` ou removida com confirmação explícita.

Use esta skill somente como referência de segurança quando o assunto for permissão, segurança, budget, tokens, logs, rate limits ou autorização para operação Meta Ads do Ares.

## Princípios

1. Read-only primeiro; dry-run antes de write.
2. Nenhum token, senha, cookie ou secret é exibido no chat.
3. Toda mudança de campanha precisa de autorização dentro do modo aprovado.
4. Budget e billing são áreas sensíveis; billing exige double-confirm.
5. Toda ação real precisa de evidência: GET pós-ação, log ou status confirmado.
6. Rate limit é parte da arquitetura, não correção posterior.

## Permissões do piloto

```text
Pessoa          | Papel  | Pode autorizar write | Budget | Billing/token
----------------|--------|----------------------|--------|---------------
Rodolfo Mattei  | Owner  | Sim                  | Confirmação explícita | Double-confirm/never expose
Ares            | Agent  | Não decide sozinho   | Não altera no piloto  | Não expõe/não altera
Gestores        | Futuro | A definir            | A definir             | Não por padrão
```

## Estados de operação

```text
Modo              | Comportamento
------------------|----------------------------------------------------------
read_only          | Apenas lê Meta/API/configs e gera relatório
dry_run            | Calcula ações que faria, mas não altera Meta
recommend          | Recomenda ações e aguarda aprovação
controlled_write   | Executa ações pré-aprovadas dentro de guardrails
autonomous_guarded | Futuro; só com regras e limites formalmente aprovados
```

## Guardrails mínimos

```text
Área                  | Guardrail
----------------------|------------------------------------------------------------
Token Meta             | 1Password; nunca imprimir; reportar só item/campo/len/status
API Meta               | Cache, batch quando possível, backoff e log de erros
Budget referência      | R$1.500/dia piloto; não pausar automaticamente por teto
Campanha TEST          | Carência 3 dias contra pausa/exclusão automática
Reativar-todas         | Lista de exclusão manual permitida; perguntar antes de adicionar
Write campanha         | Só nível campaign no piloto; validar before/after
Logs Discord           | Resumidos; intraday só se ação/erro
Auditoria local        | Salvar decisão, regra, métrica, status antes/depois e timestamp
```

## Ao usar 1Password

- Buscar item `Token Meta API` apenas internamente.
- Se precisar reportar, usar formato seguro:

```text
Item 1Password | Status | Campo usado | Len
---------------|--------|-------------|----
Token Meta API | OK     | <campo>     | <número>
```

Nunca colocar o valor do token na resposta, em arquivo de log, em traceback ou em comando impresso.

## Rate limit, throttling e cache

- Intraday roda a cada 30m, não em loop contínuo.
- Todas as chamadas Meta API devem passar por `/root/mgs-agent/scripts/ares-meta-common.py`.
- Espaçamento mínimo entre chamadas: `ARES_META_MIN_INTERVAL_SECONDS`, default `0.75s`, com lock cross-process para evitar rajadas simultâneas.
- Ao detectar rate limit, parar a sequência normal e aplicar backoff acumulado: `30s → 60s → 120s → 240s → 150s`, total máximo `600s`.
- Se continuar rate-limit após 10 minutos acumulados, parar e alertar Rodolfo no canal/thread atual quando interativo; em cron, retornar erro estruturado `ARES_RATE_LIMIT_EXHAUSTED` para entrega pelo scheduler/gateway.
- Cachear insights por janela de execução.
- Preferir buscar campos necessários de uma vez, mas evitar payloads pesados em massa como `adcreatives.object_story_spec` para muitos itens.

## Aprovação para mudanças sensíveis

```text
Mudança                         | Exigência
--------------------------------|------------------------------------------------------------
Pausar/reativar campanha         | Permitido só quando controlled-write estiver aprovado
Alterar budget                   | Confirmação explícita de Rodolfo
Criar campanha automaticamente   | Fase futura; só com budget liberado e spec aprovada
Billing/pagamento                | Double-confirm obrigatório
Token/permissão/app Meta         | Não alterar sem aprovação explícita
Tracking/pixel/CAPI              | Não alterar sem aprovação explícita
```

## Reporte de sucesso

Antes de dizer que uma ação real foi executada:

1. Confirmar resposta da API de write.
2. Fazer GET na campanha/conta afetada.
3. Registrar audit log local.
4. Enviar resumo no canal de log configurado.

Se qualquer etapa falhar, reportar como parcial/falha, não como sucesso.
