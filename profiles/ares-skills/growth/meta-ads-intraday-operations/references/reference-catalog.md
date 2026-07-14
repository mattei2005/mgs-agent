# Catálogo de referências Meta Ads intraday

Os arquivos datados listados abaixo são históricos e podem conter nomenclatura antiga (`R1–R5`, `reativar-todas`, `subs/CPS`). Em conflito, `SKILL.md` e os contratos `current-*` vencem.

## Referências

- `references/openzedfinanzas-cc-es-pilot.md` — decisões, estrutura criada, validações read-only e lições reutilizáveis do primeiro piloto Meta Messenger.
- `references/threshold-calibration.md` — método read-only de baixa carga para analisar mês da conta e sugerir thresholds R1-R5 sem pedir payload pesado da Meta API.
- `references/openzedfinanzas-cron-logging-2026-06-17.md` — detalhe da configuração dos crons intraday/reativar-todas e formato de tabela corrigido por Rodolfo para `logs-aquisicao`.
- `references/cron-log-format-logs-aquisicao.md` — formato validado por Rodolfo para logs dos crons Meta em `logs-aquisicao`: título conta/dia/horário e colunas `PG ID`, `País/Vertical`, `Regra usada`, `Status`.
- `references/meta-crons-dry-run-and-logging-2026-06-17.md` — configuração e validações dos crons dry-run/logging.
- `references/read-only-calibration-and-human-feedback-loop-2026-06-19.md` — correção operacional de Rodolfo: fase atual é calibração read-only com recomendações em thread, decisão humana, state local para pausas e write só depois de aprovação.
- `references/controlled-write-elena-bulk-and-readonly-calibration-2026-06-19.md` — ponte entre calibração read-only e controlled-write explícito: IDs de recomendação, escopo Elena/hold Patricia, desligar regras Meta de pause, normalização USD25/1 adset/3 ads e duplicação controlada para chegar a 20 campanhas.
- `references/elena-controlled-write-midnight-structure-2026-06-19.md` — padrão para controlled-write explicitamente aprovado: validar estado vivo, clarificar escopo quando contagem solicitada não bate com a conta, desativar regras Meta de PAUSE com GET, agendar one-shot na virada da conta e reportar permissões Discord via Zeus quando Ares não tiver admin token.
- `references/logs-aquisicao-threaded-cron-and-permissions.md` — padrão para postar relatórios Meta no `logs-aquisicao` abrindo thread própria via wrapper/script-only cron, evitar duplicidade de scheduler e aplicar/validar permission overwrites quando Ares tiver permissão.
- `references/hermes-script-only-timeout-and-sanitized-errors-2026-06-19.md` — padrão para impedir que crons script-only Hermes estourem o timeout de 120s do scheduler durante backoff/rate-limit Meta; wrapper deve limitar tempo total e converter falha em alerta sanitizado + audit local.
- `references/hoa-focused-page-reporting-and-discord-format.md` — regra atual do HOA por página em foco: listar todas as campanhas da página ativa, colunas preferidas por Rodolfo, e pitfall de chunking Discord sem quebrar blocos ```text.
- `references/smart-bidding-hoa-roi-reconciliation.md` — reconciliação ROI Smart Bidding × spend Meta, Auth0 PKCE, consulta histórica por intervalo/DATE, semântica cashflow e layout Openzed com ROI Drip + Total visíveis e Broadcast somente no audit.
- `references/hoa-thread-routing-historical-reports-and-mobile-layout-2026-06-22.md` — separação Intraday vs HOA em threads fixas, adição/validação de gestores+Geizian na thread, geração de HOA histórico por data/checkpoint, e layout mobile-first para evitar tabelas feias/quebradas.
- `references/discord-mobile-table-and-report-infra-pitfalls-2026-06-22.md` — lições de layout mobile-first para tabelas intraday e pitfall de REPORT-INFRA do Ares: usar `ares-report-infra.sh`, não helper que cria thread.

