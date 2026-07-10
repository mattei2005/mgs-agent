## SEÇÃO C — Hook git post-commit com notificação Discord

### Quando usar
- Notificar canal Discord automaticamente após commits interativos do Rodolfo no mgs-agent
- Auditoria de mudanças de infra em tempo real

### ⚠️ PITFALL CRÍTICO: filtro por autor não funciona

O repo `/root/mgs-agent` tem `user.name=Rodolfo Mattei` para todos os commits (auto-commits do watcher, Atena, manuais). **Filtro `%an/%ae` não discrimina.**

### ✅ Solução validada: TTY check

- SSH interativo do Rodolfo → TTY ativo
- Auto-commit watcher (systemd) → sem TTY
- Gateways Zeus/Atena (systemd) → sem TTY
- Crons → sem TTY

```bash
# Capturar ANTES do subshell background (herda via variável)
IS_INTERACTIVE=0
if [ -t 0 ] || [ -t 1 ] || [ -t 2 ]; then
  IS_INTERACTIVE=1
fi
# No subshell, verificar $IS_INTERACTIVE
```

**CRÍTICO:** capturar `IS_INTERACTIVE` no processo pai (antes do `( ) & disown`). O subshell herda variáveis mas não acessa o TTY do pai após fork.

### Hook post-commit (versão produção)

Localização: `/root/mgs-agent/.git/hooks/post-commit`

Instalar: copiar conteúdo do arquivo de referência `references/git-hook-post-commit.sh` para o hook e `chmod +x`.

Webhook URL: 1Password → vault `MGS Conteúdo` → item `Discord Webhook - Alerts Infra Channel` → campo `label=webhook_url` (não `url`) para REPORT-INFRA/alertas; usar `Discord Webhook - Zeus Channel` apenas para hook de commit interativo quando explicitamente aplicável.

### Pitfalls do hook

1. **`op` sem token no cron/background:** sempre `source /root/mgs-agent/.env` explicitamente no subshell
2. **URL hardcoded:** nunca. URL no 1Password, lida em runtime
3. **curl sem timeout:** usar `--max-time 5`; Discord pode estar offline
4. **Erros silenciosos:** usar `|| true` e `2>/dev/null` em tudo Discord; o push para GitHub NUNCA pode falhar por causa da notificação
5. **Identidade git compartilhada:** não filtrar por `%an/%ae` — usar TTY check
6. **`mapfile` em commits vazios:** `diff-tree` retorna vazio para `--allow-empty`; embed aparece sem lista de arquivos (inofensivo)
7. **Não testar via `terminal()` do Zeus:** subshell não tem TTY; testar via SSH direto do Rodolfo
8. **Commit local ≠ upload GitHub:** ao reportar commits para Rodolfo, diferenciar explicitamente `commit local`, `push/upload para GitHub`, `upstream configurado` e `auto-push confirmado`. Se a branch não tem upstream (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` falha), dizer que o commit ainda não está confirmado no GitHub e nomear o comando de push necessário, em vez de usar só o termo técnico “upstream”.

---
## SEÇÃO D — Diagnóstico, Cron Scheduler e Reinicialização de Agente (Gateway Hermes)

### Quando usar
- Agente está online (processo rodando) mas não responde no Discord
- Mensagens não aparecem como `inbound message` no log
- Agente travou em loop de rate limit
- Usuário relata silêncio após período de alta atividade
- Auditar ou migrar cron jobs Hermes/Linux entre profiles MGS

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

### Approval buttons no Discord: prompts frequentes e “This interaction failed”

Quando Rodolfo relatar que botões `Allow Once / Allow Session / Always Allow / Deny` falham com “This interaction failed” ou aparecem com frequência excessiva, usar o playbook em `references/hermes-discord-approval-buttons.md`.

Resumo operacional:
- Diagnosticar em `errors.log`, `agent.log`, `gateway/platforms/discord.py` e `tools/approval.py` antes de mudar config.
- Se o handler editar a mensagem antes de dar ACK, patchar para `await interaction.response.defer(ephemeral=True)` imediatamente e só depois resolver a fila Hermes / editar `interaction.message`.
- Para reduzir ruído de falso positivo em operações MGS conhecidas, preferir `approvals.mode: smart` + `approvals.gateway_timeout: 900`, preservando hardline blocks.
- Não desligar aprovações globalmente (`mode: off`) sem autorização explícita; isso remove uma camada de segurança.
- Após patch em runtime Hermes, `py_compile` e restart controlado do gateway afetado são obrigatórios antes de declarar mitigação ativa.

### Discord mostrando retry/TTFB técnico em toda mensagem

Quando Rodolfo relatar que Zeus/Atena está postando mensagens técnicas como `Retrying in ...`, `No first byte from provider in 45s`, rate-limit waits, ou falhas auxiliares dentro das threads, tratar como **ruído de status callback**, não como motivo automático para trocar modelo/provider.

### Live tool-call trace no Discord com cleanup automático

Quando Rodolfo quiser a UX de “atividade ao vivo” no Discord — tool calls visíveis enquanto o agente trabalha e removidos quando a resposta final chega — usar `references/discord-live-tool-trace-cleanup.md`.

Correção MGS validada: **não confundir live progress com poluição de Discord**. Para Rodolfo, “poluição” normalmente significa loop/conversa infinita entre agentes, ACK/status chatter ou bot acordando outro bot sem necessidade — não breadcrumbs curtos de progresso. Ver `references/discord-live-progress-vs-agent-loop-pollution-2026-06-16.md`.

Resumo operacional:
- Ativar `display.platforms.discord.tool_progress: all` e `tool_preview_length` adequado por profile.
- Ativar `display.platforms.discord.cleanup_progress: true` para apagar breadcrumbs após sucesso.
- Manter `interim_assistant_messages: false` quando o objetivo for progresso limpo sem conversa extra.
- Garantir que o adapter Discord implemente `delete_message`; sem isso o runner desativa cleanup silenciosamente.
- Aplicar config nos profiles ativos e nas cópias versionadas em `/root/mgs-agent/profiles/*-config.yaml`.
- Validar YAML/valores efetivos, registrar audit log e reiniciar gateways por restart seguro/detached quando a mudança precisar entrar em runtime; Zeus por último.
- Não desligar live progress como “anti-poluição” se o problema real for loop entre agentes; corrija filtros/mentions/lifecycle notices no fluxo multiagente.

Padrão correto:
- Confirmar o sintoma no print/logs (`agent.log`/`errors.log`) e distinguir: retry interno pode continuar, mas não deve poluir Discord.
- Corrigir no gateway em `_prepare_gateway_status_message(...)`, aplicando a supressão de status ruidoso também para `Platform.DISCORD`.
- Manter logs completos; só suprimir o envio ao chat.
- Atualizar teste de gateway para cobrir Telegram + Discord.
- Rodar `py_compile` + pytest do filtro e reiniciar os gateways afetados.

Referência detalhada: `references/discord-provider-retry-noise-filter.md`.

