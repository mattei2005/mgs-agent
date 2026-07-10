## Meta Ads intraday / chatbot operations

Quando Rodolfo pedir gestão de tráfego Meta Ads, cortes intraday, reativação de campanhas, Messenger/chatbot, CPS/subscribers, ou operação determinística de campanhas, carregar também:

- `meta-ads-intraday-operations` — processo intraday: R1-R5, reativar-todas, carência TEST, logs e auditoria.
- `meta-ads-governance-guardrails` — permissionamento, token, budget, rate limit, auditoria e transição read-only/dry-run/write.

Padrão aprendido no piloto Meta Messenger: separar **crons determinísticos** (reativar-todas e cortes intraday) da camada **gestor inteligente/head de aquisição**. Intraday deve executar regras objetivas por operação país+vertical, com logs resumidos apenas quando houver ação/erro. Não misturar ROI externo/Lovable no primeiro corte determinístico antes de mapear a métrica Meta correta de CPS/subscriber.

Pitfalls específicos:

- Não assumir moeda do teto informado pelo usuário; validar `currency` da conta Meta. Se divergir (ex.: usuário fala R$ e conta retorna USD), registrar como referência e não usar como kill switch sem confirmação.
- Não usar `reativar-todas` sem lista de exclusão configurável; a lista pode começar vazia, mas perguntar antes de adicionar qualquer campanha.
- Não pausar campanha com `TEST` no nome durante carência de 3 dias; preferir `created_time` da Meta, fallback para `first_seen_at` local.
- Não enviar log intraday a cada 30 minutos se nada aconteceu, salvo política explícita diferente.
- Não reportar leitura Meta como sucesso sem HTTP real da Graph API e sem ocultar token no relatório.
- Se scripts Meta/cron começarem a dar timeout segurando `meta-api-throttle-state.json`, verificar drift de `time.monotonic()` persistido após reboot antes de culpar Graph/API. Corrigir o throttle para zerar `last_request_monotonic` quando `last > now` e limitar sleep ao intervalo configurado. Referência: `references/meta-api-throttle-monotonic-reboot.md`.
