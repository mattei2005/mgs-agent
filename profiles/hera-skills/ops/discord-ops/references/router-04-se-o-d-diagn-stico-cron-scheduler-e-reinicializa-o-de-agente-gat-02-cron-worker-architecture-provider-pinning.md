### Cron-worker architecture / provider pinning

Ver `references/hermes-cron-worker-architecture.md` para o padrão completo de auditoria e migração.

Para estabilidade pós-migração Codex OAuth, ver também `references/hermes-codex-oauth-and-auxiliary-compression.md`: padrão híbrido GPT-5.5 Codex como modelo principal + auxiliares Haiku/Anthropic, sync OAuth global→profiles via cron, validação de restarts e pitfalls de chat-log com `$`.

Resumo operacional MGS:
- `zeus` e `atena` ficam em `gpt-5.5` via `openai-codex` para trabalho principal.
- Cron com LLM deve rodar no profile dedicado `cron-worker` usando `claude-haiku-4-5-20251001` via `anthropic`.
- Cron determinístico deve ser script-only ou Hermes `no_agent=True`; não gastar LLM.
- Para modelos Claude, não confiar em `provider: auto` quando o profile default é `openai-codex`; pin explícito: `provider: anthropic`.
- Erro `model is not supported when using Codex with a ChatGPT account` para Haiku geralmente indica provider errado, não ID de modelo inválido.

Antes de mudar cron/profile/service, fazer Fase 1 read-only: configs dos profiles, `cron/jobs.json`, `crontab -l`, `systemctl cat`, e reportar sem restart/write.

