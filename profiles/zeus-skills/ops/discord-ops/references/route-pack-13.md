### Threads antigas continuam abertas na sidebar de usuários adicionados

Quando Rodolfo mostrar screenshot ou relatar que Geizian/gestores/Kelly veem muitas threads antigas abertas após serem adicionados por auto-add, trate como problema de **stale active threads**, não apenas de política de membros. Consulte `references/discord-stale-thread-archive-enforcement-2026-06-30.md`.

Checklist curto:
1. Auditar `/guilds/{guild_id}/threads/active` com os bot tokens dos profiles afetados.
2. Para cada parent channel de Zeus/Atena/Ares/agente legado, comparar `thread_metadata.archived`, `auto_archive_duration` e timestamp do `last_message_id`.
3. Se `last_message + auto_archive_duration + grace` já passou e `archived=false`, arquivar via `PATCH /channels/{thread_id}` com `{"archived": true}`.
4. Manter auto-add e archive como assuntos separados: remover usuário reduz escopo de notificação, mas não corrige thread stale.
5. Se a correção virar script/cron/config/data, atualizar inventário/audit log e seguir o fluxo REPORT-INFRA.

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

### Leitura sob demanda de threads antigas

Quando Rodolfo perguntar se Zeus consegue ler threads antigas, responder com precisão: Zeus não lê automaticamente qualquer thread antiga pelo contexto ativo, **mas consegue importar uma thread específica por link/ID em modo read-only**. Não diga “não consigo ler thread por ID” quando há um ID/link disponível — execute o importador primeiro.

Referências e playbooks:
- `references/discord-thread-importer.md`
- `references/discord-thread-import-readonly-correction-2026-06-12.md` — correção validada após Zeus responder incorretamente que não conseguia ler thread por ID.

Fluxo padrão:
1. Rodolfo fornece link Discord ou thread/channel ID.
2. Rodar `/root/mgs-agent/scripts/import-discord-thread.py --profile zeus --limit 1000 '<link-ou-id>'`.
3. Ler `/root/mgs-agent/data/discord-thread-imports/<thread_id>.md` ou `.json` para responder.
4. Se a conversa for grande, preferir `--limit 1000` em vez de `--limit 200` para não perder o começo.
5. Reportar contagem de mensagens, período, snapshot e modo read-only.
6. Manter `data/discord-thread-imports/` local-only no `.gitignore`; não versionar históricos importados.

Pitfall crítico: separar “não recebo automaticamente o histórico completo na janela ativa” de “não consigo ler histórico”. A primeira frase é verdadeira; a segunda é falsa quando o bot tem acesso e o importador está disponível.
5. Manter `data/discord-thread-imports/` local-only no `.gitignore`; não versionar históricos importados.

---
## SEÇÃO G — Importar histórico de thread antiga por link/ID

Quando Rodolfo/Raquel pedir para Zeus, Atena, Ares, agente legado ou outro agente MGS ler uma thread antiga, use o importador read-only canônico por link/ID. Ver `references/discord-thread-history-import.md` e `references/discord-thread-import-profile-rollout.md`.

Comandos padrão:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile legacy-agent '<LINK_OU_ID>'
```

Regra operacional: nunca responder “só leio o contexto entregue pelo gateway” quando Rodolfo fornece ID/link antes de tentar o importador com o profile correto. O contexto ativo pode não conter histórico completo; isso é diferente de incapacidade de importar histórico read-only.

Pitfalls:
- Usar o `--profile` correto evita tentar acessar private threads com o token do bot errado.
- Se retornar `403 Missing Access`, reportar falta de acesso real do bot do profile à thread/canal e pedir liberação; não inventar conteúdo.
- Para agentes novos, garantir que o `import-discord-thread.py` aceite o profile sem lista hardcoded restrita. Validado após remover `choices=["zeus","atena"]` e validar nomes por regex segura.
- Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
## SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)
- Usar o `--profile` correto evita tentar acessar private threads com o token do bot errado.
- Se `GET /channels/<thread_id>` retornar `403 Missing Access`, é uma limitação de permissão do bot/profile naquela thread/canal; reporte isso claramente e não invente conteúdo.
- Não confundir `403 Missing Access` para enviar mensagem no canal Zeus/home com incapacidade de ler uma thread acessível: são permissões separadas.
- Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
## SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)

