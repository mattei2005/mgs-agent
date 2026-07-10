# Operational Posture and MGS Environment

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## Postura operacional

- Trabalhar sempre contra o estado vivo da instalação; não responder de memória.
- Antes de ação destrutiva ou restart, checar contexto, risco e impacto nos gateways.
- Não vazar tokens/API keys. Reportar provider, item/vault/field e presença/len quando necessário.
- Separar claramente: ferramenta habilitada, backend configurado, credencial presente e backend realmente utilizável.
- Preferir output executivo em PT-BR para Rodolfo: conclusão primeiro, evidências e próximo passo concreto.
- Para bloqueios de referência YouTube/Shorts em VPS, não recomendar Browserbase/proxy pago como primeira resposta se o uso for ocasional. Validar primeiro o caminho sem custo extra: Chromium persistente, sessão/cookies persistentes uma vez, ou vídeo anexado. Browserbase/residential proxy só entra se o volume recorrente justificar custo operacional.

## Ambiente MGS conhecido

- Profiles principais: `/root/.hermes/profiles/zeus/`, `/root/.hermes/profiles/atena/` e `/root/.hermes/profiles/ares/`.
- Checkout Hermes: `/root/.hermes/hermes-agent`.
- Gateways systemd: `zeus-gateway.service`, `atena-gateway.service` e `ares-gateway.service`.
- Projeto MGS: `/root/mgs-agent/`.
- Alguns comandos de restart em Zeus podem interromper a sessão atual; planejar janela quando necessário.
- Padrão MGS para próximos restarts de Zeus/Atena/Ares: preferir `/restart` no próprio agente/thread ou restart gracioso via SIGUSR1/Hermes gateway restart, porque drena execuções em andamento e preserva melhor sessão/thread. `systemctl restart` fica como fallback para agente travado/offline, falha do `/restart` ou emergência operacional.
- Nuance validada em teste Zeus 2026-06-02: antes do patch MGS, o restart gracioso preservava a sessão/thread e retomava com o mesmo session_id após nova mensagem do usuário, mas não continuava automaticamente sozinho depois de subir. A resposta final emitida durante o drain podia não aparecer no Discord antes da desconexão.
- Patch local MGS aplicado em `gateway/run.py`: em restart planejado, manter `resume_pending` mesmo quando o drain completa limpo para sessões ativas no momento do restart. Objetivo: no startup, `_schedule_resume_pending_sessions()` sintetiza um evento interno na mesma thread e Zeus/Atena/Ares continuam sem Rodolfo precisar escrever `retoma`. Validar com `py_compile` + `tests/gateway/test_gateway_shutdown.py::test_planned_restart_keeps_resume_pending_after_graceful_drain` + `tests/gateway/test_restart_resume_pending.py`.
