### Live tool-call trace no Discord com cleanup automático

Quando Rodolfo quiser a UX de “atividade ao vivo” no Discord — tool calls visíveis enquanto o agente trabalha e removidos quando a resposta final chega — usar `references/discord-live-tool-trace-cleanup.md`.

Resumo operacional:
- Ativar `display.platforms.discord.tool_progress: all` e `tool_preview_length` adequado por profile.
- Ativar `display.platforms.discord.cleanup_progress: true` para apagar breadcrumbs após sucesso.
- Garantir que o adapter Discord implemente `delete_message`; sem isso o runner desativa cleanup silenciosamente.
- Aplicar config nos profiles ativos e nas cópias versionadas em `/root/mgs-agent/profiles/*-config.yaml`.
- Validar com `py_compile` + parse YAML/AST sem restart; pedir autorização separada para reiniciar gateways.

Padrão correto:
- Confirmar o sintoma no print/logs (`agent.log`/`errors.log`) e distinguir: retry interno pode continuar, mas não deve poluir Discord.
- Corrigir no gateway em `_prepare_gateway_status_message(...)`, aplicando a supressão de status ruidoso também para `Platform.DISCORD`.
- Manter logs completos; só suprimir o envio ao chat.
- Atualizar teste de gateway para cobrir Telegram + Discord.
- Rodar `py_compile` + pytest do filtro e reiniciar os gateways afetados.

Referência detalhada: `references/discord-provider-retry-noise-filter.md`.

