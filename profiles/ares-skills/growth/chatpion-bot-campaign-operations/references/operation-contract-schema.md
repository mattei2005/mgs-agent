# Schema do contrato por operação

Cada consumidor da família `chatpion_bot_messenger` mantém identidade e valores fora da skill principal.

## Campos obrigatórios

- `operation_id`, site/domínio, país, vertical e idioma;
- alias e caminho da conta Meta;
- moeda, timezone, owners e autoridade;
- `strategy_binding.family_id` e versão mínima;
- contrato Engine e `supported_modes`;
- Page/UTM/PBIA, evento, pixel e JSON aplicáveis;
- estrutura, copy, criativos e naming;
- thresholds, comparadores, fases, horários e budgets;
- guardrails, holds, freshness e ações permitidas;
- routes, prompts, runners, states, audits e crons;
- flags de write e activation.

## Proibido herdar

Credenciais, billing, IDs técnicos da fonte, campaigns, media IDs, Pages, states, denylist, baselines, performance, request IDs, locks, schedules e autoridade operation-scoped.

## Regra de override

O contrato de família define o mecanismo e os campos exigidos. O contrato da operação fornece valores e exceções. Ausência não significa usar o valor de outro consumidor; significa falhar fechado.
