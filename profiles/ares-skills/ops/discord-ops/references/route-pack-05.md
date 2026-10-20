### Causa raiz difícil: Message Content Intent

Se após reinicialização o agente **continua sem receber**: verificar no Discord Developer Portal:
1. https://discord.com/developers/applications → aplicação do bot
2. Aba **Bot** → **Privileged Gateway Intents** → confirmar **Message Content Intent** habilitada

### Patch local `busy_input_mode` em gateway

Patch em `/root/.hermes/hermes-agent/gateway/run.py` que faz `busy_input_mode: queue` funcionar em gateway mode. Quando o Hermes for atualizado:
1. Verificar: `grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py`
2. Se não estiver: `patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch`
3. Validar o patch e os testes antes de qualquer ativação. Se for necessária reinicialização, seguir `references/gateway-restart-coordination.md` pela rota segura/detached autorizada; não reiniciar o gateway próprio ou relacionado dentro da sessão ativa nem incluir outro profile por conveniência.

Issue upstream: https://github.com/NousResearch/hermes-agent/issues/14905

### Pitfalls (restart)

- **Separar manutenção, reinicialização e validação.** Não combinar patch, restart e cron com agente na mesma sessão operacional: o drain pode interromper a execução e uma checagem entregue na origem pode produzir novos resíduos. Aplicar a mudança mínima e testar; quando a ativação exigir restart autorizado, usar a coordenação segura/detached e validar o serviço por leitura direta. Para etapa diferida, preferir verificação determinística com saída local, sem resposta automática do modelo na conversa.
- **Restart sob systemd pode ficar `deactivating/stop-sigterm` enquanto drena turno ativo.** Não declarar travamento imediatamente; verificar logs por `Shutdown phase: drain done` e novo `Connected as ...`. Se o usuário está aguardando ação operacional, manter resposta curta e não abrir novos loops de diagnóstico.
- **Roteamento Zeus/Atena:** se Zeus precisa ler o canal da Atena mas não responder a pedidos editoriais, manter `allowed_channels` incluindo Atena apenas com `require_mention=true`, `thread_require_mention=true` e `free_response_channels` restrito ao canal Zeus. Validar com logs que pedido normal no canal Atena não vira thread duplicada do Zeus.
- **Não usar `nohup/disown/&`** em terminal foreground — usar `terminal(background=true)`
- **Sessão zumbi é silenciosa** — Discord mostra online mas sem eventos; detectável só pelo log
- **`pkill` pelo padrão exato** — `pkill -f "hermes -p atena gateway run"` para não matar outros perfis
- **`config.yaml` sobrescreve `.env` para `allowed_channels`** — se `discord.allowed_channels` estiver vazio, agente ignora TODAS as mensagens. Fix: `allowed_channels: '1496267571543019653'` no `config.yaml`
- **Mensagens de bots ignoradas por padrão** — `DISCORD_ALLOW_BOTS=mentions` no `.env` do agente destino; com `mentions`, incluir `<@BOT_ID>` no texto
- **Profile `.env` real está em `/root/.hermes/profiles/{agent}/.env`** — nunca `/root/.hermes/.env` (é template)
- **Instância em terminal interativo (`pts/N`)** — output vai para aquele terminal, não para agent.log; detectar via coluna TTY no `ps aux`
- **Múltiplas instâncias conflitam** — verificar PID file antes de reiniciar; `Another gateway instance is already running`

### Progresso residual e notificações tardias

1. **Separe o que ficou visível.** Inspecione o print real e classifique progressos de ferramentas, mensagens intermediárias do assistente, avisos de processos em segundo plano e resposta final. Esses tipos podem ter transportes e ciclos de limpeza diferentes; um aviso `exit 1` não comprova falha do cron nem da limpeza.
2. **Reconcilie a operação primeiro.** Consulte o checkpoint e a fonte canônica apontada. Compare horário e identidade da tentativa avisada com a preparação validada, a agenda registrada e os recibos de entrega do mesmo pedido. Mantenha as distinções preparado/agendado/publicado; uma notificação antiga não justifica replay nem uma nova resposta a um pedido já encerrado.
3. **Confirme a configuração efetiva sem modificá-la.** Projete somente `display.platforms.discord.cleanup_progress`, `tool_progress` e o agrupamento correspondente. Resolva a precedência pelos helpers de configuração do runtime atual. `cleanup_progress=true` expressa intenção, não prova que algum DELETE foi executado; preserve o progresso ao vivo exigido pelo usuário.
4. **Siga o mecanismo do runtime, não uma hipótese.** No código ativo, localize `_run_agent_schedule_bubble_cleanup`, `_track_progress_result` e o callback de pós-entrega. Confira se os IDs foram rastreados no turno correto, se a resposta foi classificada como falha e se o callback ficou vinculado à sessão/geração que realmente entregou a resposta final. O mecanismo consultado pode reter rastros de execuções falhadas e suprimir exceções de exclusão; confirme a implementação vigente antes de aplicar essa interpretação.
5. **Limite a conclusão ao que os logs provam.** Correlacione apenas a janela da execução e sua sessão. Sem registro de tentativa/resultado de exclusão, não afirmar que faltou permissão, houve rate limit ou um erro de ferramenta interrompeu a limpeza. Progresso ainda visível mais configuração ativa prova que a limpeza esperada não foi confirmada, não sua causa específica. Não reiniciar gateway nem alterar configuração para completar o diagnóstico.
6. **Se houver autorização de limpeza manual, opere por IDs.** Inventarie somente mensagens temporárias do pedido, confirme thread/pai/autor/conteúdo e preserve humanos, conclusões e relatórios. Após cada exclusão, confirme ausência do ID exato. Apagar resíduos não corrige automaticamente o mecanismo que os deixou; correção de código/configuração é escopo separado.

Para uma correção autorizada do mecanismo, exigir regressões que cubram sucesso com resposta final entregue, execução falhada com retenção prevista, callback de geração obsoleta, falha de DELETE e aviso tardio já reconciliado sem nova resposta ou replay. Testes locais não substituem o readback da conversa real. Não declarar causa resolvida ou limpeza concluída apenas pela configuração ou por um teste offline.

### Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```

---
