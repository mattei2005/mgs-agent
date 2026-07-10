### Processamento Zeus de REPORT-INFRA com cron Hermes de outro profile

Quando um agente reportar criação/modificação de cron Hermes `no_agent` + script wrapper em outro profile (ex: Ares):
1. Validar evidência mínima sem expor segredo: `py_compile` do script real, `bash -n` do wrapper, `sha256sum` dos paths reportados e leitura sanitizada do `~/.hermes/profiles/<agent>/cron/jobs.json` para confirmar `id`, `enabled`, `state`, `next_run_at`, `script`, `no_agent` e `deliver`.
2. Atualizar `/root/mgs-agent/data/infra-inventory.json` com:
   - script versionado em `/root/mgs-agent/scripts/...`;
   - wrapper/profile script fora do repo, se for parte runtime do cron;
   - registro do cron Hermes com `profile`, `id`, `schedule`, `script`, `next_run_at`, `state`, `enabled`, `no_agent` e `deliver`.
3. Registrar `report_infra_processed` em `events-audit.jsonl` com validações executadas.
4. Commitar somente os artefatos versionáveis relevantes (`data/infra-inventory.json` e script em `/root/mgs-agent/scripts/...`). Não tentar `git add` path fora do repo; registre-o no inventário.
5. Responder só depois do processamento completo, no formato curto acima.

