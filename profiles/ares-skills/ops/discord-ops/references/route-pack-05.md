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

1. **Classifique os alvos reais.** Quando houver IDs, leia essas mensagens na thread indicada; use o print somente quando necessário. Separe progressos de ferramentas, mensagens intermediárias, avisos de processos e resposta final, pois os transportes e ciclos de limpeza podem diferir. Não inclua progresso de uma rodada nova só porque aparece na mesma thread.
2. **Reconcilie a operação e responda ao status pedido.** Consulte mensagens atuais, checkpoint e recibo canônico do request exato. Compare tentativa, horário e estado validado; reconcilie as contagens dos recibos em código antes de repeti-las. Distingua preparado, implementado, validado, publicado e agenda habilitada. Uma notificação tardia não autoriza replay nem outra confirmação espontânea de trabalho já encerrado.
3. **Limpe os IDs autorizados antes do diagnóstico extenso.** Inventarie thread/pai/autor/conteúdo e congele somente os temporários encerrados. Use `discord_admin.delete_message` ou o transporte próprio autorizado, seguido de GET direto de cada mensagem. Exija `404` com código `10008` para confirmar ausência; outro erro não comprova exclusão. Faça também GET das conclusões e mensagens humanas selecionadas para provar preservação. Persista o recibo sem apagar ou interferir na execução nova. Se faltar autorização, mantenha a limpeza separada e peça somente o escopo indispensável.
4. **Confirme a configuração sem modificá-la.** Projete somente `display.platforms.discord.cleanup_progress`, `tool_progress` e o agrupamento correspondente; resolva a precedência pelos helpers do runtime atual. Configuração em disco expressa intenção, não comprova carregamento no processo nem tentativa de DELETE. Preserve o acompanhamento ao vivo exigido pelo usuário.
5. **Investigue o mecanismo somente no escopo necessário.** No código ativo, localize `_run_agent_schedule_bubble_cleanup`, `_track_progress_result` e o callback de pós-entrega. Confira rastreamento dos IDs, classificação do turno e vínculo do callback à sessão/geração que entregou a resposta final. Verifique na implementação vigente qualquer retenção de rastros de falha ou supressão de exceções antes de usá-la como explicação.
6. **Feche separando as duas correções.** Informe primeiro o resultado operacional solicitado, depois quantos resíduos tiveram ausência verificada e, por fim, o estado do mecanismo automático. Sem logs de tentativa/resultado, não atribua a causa a permissão, rate limit ou falha de ferramenta. DELETE manual prova retirada dos alvos, não reparo automático; não reinicie nem altere configuração apenas para completar o diagnóstico.

Para uma correção autorizada do mecanismo, exigir regressões que cubram sucesso com resposta final entregue, execução falhada com retenção prevista, callback de geração obsoleta, falha de DELETE e aviso tardio já reconciliado sem nova resposta ou replay. Testes locais não substituem o readback da conversa real. Não declarar causa resolvida ou limpeza concluída apenas pela configuração ou por um teste offline.

### Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```

---
