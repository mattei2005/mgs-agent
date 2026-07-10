## SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico

Ver `references/discord-threads-lifecycle.md` para referência completa.

### Auto-add de membros em threads: diagnosticar prompt/config antes de culpar Discord

Quando Rodolfo relatar que Atena/Zeus cria threads mas parou de colocar pessoas automaticamente nelas, usar `references/discord-thread-auto-add-members-regression.md`. Para a correção aplicada em 2026-05-19 na Atena, ver `references/discord-thread-auto-add-members-2026-05-19.md`.

Lição validada: o gateway Discord do Hermes cria threads via `_auto_create_thread(...)`, mas não adiciona membros extras por padrão. No setup MGS, o comportamento antigo vinha de um `channel_prompts` bootstrap que fazia auto-discover + `PUT /channels/{THREAD_ID}/thread-members/{uid}` via `execute_code`. Se esse prompt/config for simplificado demais, a thread continua sendo criada, mas só ficam o usuário autor + bot/agente.

Pitfall 2026-05-26: `execute_code` pode não receber `DISCORD_BOT_TOKEN`; o env passthrough bloqueia credenciais de provider/bot por segurança. Se logs mostrarem `env passthrough: refusing ... DISCORD_BOT_TOKEN` ou `ERROR: DISCORD_BOT_TOKEN not set`, o bootstrap em prompt não consegue chamar Discord API. Preferir correção no runtime/gateway ou script shell que carregue o `.env` autorizado fora do sandbox, e validar com API/logs antes de declarar auto-add corrigido.

Regra operacional atual por agente/canal:
- Atena/content threads devem auto-add Raquel (`1496254952501280974`) + Rodolfo (`344196393512075265`).
- Zeus/admin threads atualmente só exigem Rodolfo.
- Hera/creative threads devem auto-add Rodolfo (`344196393512075265`), Kelly (`1291113428982693940`), Geizian (`321263240782807040`) e gestores de tráfego aprovados: Icaro (`409878085807112207`), Isliago (`432898782188011543`), Joe (`1214246869484576890`) e Nicolas (`1055570806945620030`).
- Não adicionar todo mundo do guild/canal; usar política explícita por agente/canal.

Quando Rodolfo mudar a política de auto-add de um agente, atualizar os dois pontos que realmente importam: `DISCORD_THREAD_AUTO_ADD_USERS` no `.env` ativo do profile (o systemd carrega esse EnvironmentFile) e `discord.thread_auto_add_users` no `config.yaml` ativo/versionado. Validar parse YAML e reiniciar o gateway do agente para a variável entrar no processo. Se a alteração tocar profile/config/script operacional, enviar `[REPORT-INFRA]` para `#alerts-infra`.

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

Resumo operacional:
- Verificar acesso de Zeus e Atena via Discord API, mas lembrar que acesso ao canal ≠ gateway ouvindo; checar `discord.allowed_channels` separadamente.
- Preferir poller Zeus com state (`last_seen_id`/`processed`) + reply via `message_reference`, em vez de adicionar o canal ao gateway normal.
- Manter Atena fora desse fluxo por padrão; é administrativo/Hermes, não editorial.
- Inicializar state no message atual para não reprocessar histórico/follow setup.
- Ignorar state runtime no git para evitar auto-commit de churn.

Ver `references/discord-threads-lifecycle.md` para referência completa.

**Resumo executivo:** threads arquivadas = zero tokens. Tokens só correm quando chega mensagem nova. Histórico preservado indefinidamente (sem auto-delete). Canal Zeus: archive em 24h.

### Contexto perdido em thread ativa: verificar `session_reset` antes de culpar Discord

Quando Rodolfo relatar que um agente “perdeu contexto da thread”, respondeu como se fosse conversa nova, ou ignorou mensagens anteriores dentro da mesma thread, diagnosticar primeiro a sessão Hermes, não a thread Discord.

Checklist read-only:

```bash
# Config do profile afetado
python3 - <<'PY'
import yaml
p='/root/.hermes/profiles/ares/config.yaml'  # trocar profile
c=yaml.safe_load(open(p)) or {}
print(c.get('session_reset'))
print((c.get('discord') or {}).get('history_backfill'), (c.get('discord') or {}).get('history_backfill_limit'))
PY

# Sessão associada à thread e se ela reiniciou com history=0
grep -n "THREAD_ID\|Session expiry\|conversation turn: session=.*history=" /root/.hermes/profiles/ares/logs/agent.log | tail -120
```

Sinais de causa raiz:
- `Session expiry done` perto do horário diário configurado (`session_reset.at_hour`).
- Nova mensagem na mesma `thread_id/chat` cria novo `session_id` com `history=0`.
- `sessions/sessions.json` mostra a thread apontando para sessão nova, enquanto sessões antigas foram `expiry_finalized=true`.

Interpretação operacional: Discord preservou a thread; quem zerou contexto foi o Hermes por política de reset/expiração. Para threads operacionais longas (Canva/downloads/campanhas), o padrão recomendado é evitar reset diário rígido e usar expiração por inatividade maior:

```yaml
session_reset:
  mode: idle
  idle_minutes: 10080   # 7 dias, ajustar por perfil
  at_hour: 4
```

Aplicar mudança de config e restart de gateway só com autorização explícita quando afetar serviço ativo. Após restart, validar `systemctl is-active <agent>-gateway.service` e log com `Connected as ...` + próxima mensagem entrando com histórico esperado.

### Leitura sob demanda de threads antigas

Quando Rodolfo perguntar se Zeus consegue ler threads antigas, responder com precisão: Zeus não lê automaticamente qualquer thread antiga pelo contexto ativo. A solução operacional é importar uma thread específica por link/ID via Discord API em modo read-only.

Referência e playbook: `references/discord-thread-importer.md`.

Fluxo padrão:
1. Rodolfo fornece link Discord ou thread/channel ID.
2. Rodar `/root/mgs-agent/scripts/import-discord-thread.py '<link-ou-id>'`.
3. Ler `/root/mgs-agent/data/discord-thread-imports/<thread_id>.md` para responder.
4. Manter `data/discord-thread-imports/` local-only no `.gitignore`; não versionar históricos importados.

---
