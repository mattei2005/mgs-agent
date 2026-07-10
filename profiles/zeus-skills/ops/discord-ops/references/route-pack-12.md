### Pitfalls (restart)

- **Não combinar patch + restart + cron/LLM check no mesmo fluxo ativo sem necessidade.** Incidente 2026-05-18: restart de `zeus-gateway` durante uma conversa grande gerou `SIGTERM`, drain de ~106s, mensagens de “Gateway shutting down”, e um cron de pós-check concorreu com o turno seguinte. Para patch urgente de gateway: aplicar mudança mínima, validar sintaxe, fazer `systemctl restart <service>`, checar `systemctl show/is-active` diretamente após voltar, e evitar criar cron LLM entregue na origem como healthcheck; se precisar watchdog, usar script-only/no-agent silencioso.
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

### Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```

---
## SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico

Ver `references/discord-threads-lifecycle.md` para referência completa.

### Auto-add de membros em threads: diagnosticar prompt/config antes de culpar Discord

Quando Rodolfo relatar que Atena/Zeus cria threads mas parou de colocar pessoas automaticamente nelas, usar `references/discord-thread-auto-add-members-regression.md`. Para a correção aplicada em 2026-05-19 na Atena, ver `references/discord-thread-auto-add-members-2026-05-19.md`.

Lição validada: o gateway Discord do Hermes cria threads via `_auto_create_thread(...)`, mas não adiciona membros extras por padrão. No setup MGS, o comportamento antigo vinha de um `channel_prompts` bootstrap que fazia auto-discover + `PUT /channels/{THREAD_ID}/thread-members/{uid}` via `execute_code`. Se esse prompt/config for simplificado demais, a thread continua sendo criada, mas só ficam o usuário autor + bot/agente.

Pitfall 2026-05-26: `execute_code` pode não receber `DISCORD_BOT_TOKEN`; o env passthrough bloqueia credenciais de provider/bot por segurança. Se logs mostrarem `env passthrough: refusing ... DISCORD_BOT_TOKEN` ou `ERROR: DISCORD_BOT_TOKEN not set`, o bootstrap em prompt não consegue chamar Discord API. Preferir correção no runtime/gateway ou script shell que carregue o `.env` autorizado fora do sandbox, e validar com API/logs antes de declarar auto-add corrigido.

Regra operacional atual: Atena/content threads devem auto-add Raquel (`1496254952501280974`) + Rodolfo (`344196393512075265`). Zeus/admin threads atualmente só exigem Rodolfo. Não adicionar todo mundo do guild/canal; usar política explícita por agente/canal.

Diagnóstico mínimo:
- Inspecionar `/root/.hermes/profiles/{atena,zeus}/config.yaml` → `discord.channel_prompts`.
- Procurar no histórico versionado por `thread-members`, `auto-discover`, `renomear thread + adicionar membros`.
- Verificar no gateway (`/root/.hermes/hermes-agent/gateway/platforms/discord.py`) se há `thread.add_user`/`thread-members`; se não houver, core não está fazendo auto-add.
- Consultar Discord API para `GET /channels/{THREAD_ID}/thread-members` e reportar apenas contagem/IDs permitidos; nunca imprimir token/header.

Correção preferida: implementar auto-add determinístico pós-criação no runtime/config (`thread_auto_add_users`/roles) ou restaurar prompt enxuto só para thread comprovadamente nova. Não voltar com script longo em toda resposta/follow-up.



### Bootstrap de novo agente Discord/Hermes

Quando criar ou colocar online um novo agente MGS no Discord (bot/app OAuth, item 1Password, `.env`, canal privado, systemd service e smoke test), usar `references/new-discord-agent-bootstrap.md`. Ele cobre scopes OAuth, campos 1Password (`discord_bot_token`, `webhook_url`), validação de guild/channel access, overwrite de permissões, template systemd e `DISCORD_THREAD_AUTO_ADD_USERS` para auto-add do Rodolfo em threads sem depender de bootstrap via `execute_code`.

### Followed announcement channels com explicação automática

Quando Rodolfo criar um canal que segue anúncios externos (ex: Hermes announcements) e pedir para Zeus explicar automaticamente cada novo post abaixo do anúncio, usar o padrão de poller cron descrito em `references/discord-followed-announcement-explainer.md`.

### Aviso antes de thread ficar oculta por auto-archive

Quando Rodolfo pedir para ser avisado antes de threads Discord configuradas com `Hide After Inactivity = 1 Week` ficarem ocultas, não criar keepalive por padrão. O padrão correto é monitor diário com alerta no sexto dia: consultar `/guilds/{guild_id}/threads/active` pelos bot tokens dos agentes MGS relevantes, filtrar `thread_metadata.auto_archive_duration == 10080`, calcular `archive_at`, deduplicar por `thread_id + archive_at` em state file local e avisar Rodolfo quando faltar até 24h. Ver `references/discord-thread-auto-archive-warning-cron.md` para implementação, validação e pitfall de verificação ad-hoc com `/tmp/hermes-verify-*`.

Resumo operacional:
- Verificar acesso de Zeus e Atena via Discord API, mas lembrar que acesso ao canal ≠ gateway ouvindo; checar `discord.allowed_channels` separadamente.
- Preferir poller Zeus com state (`last_seen_id`/`processed`) + reply via `message_reference`, em vez de adicionar o canal ao gateway normal.
- Manter Atena fora desse fluxo por padrão; é administrativo/Hermes, não editorial.
- Inicializar state no message atual para não reprocessar histórico/follow setup.
- Ignorar state runtime no git para evitar auto-commit de churn.

