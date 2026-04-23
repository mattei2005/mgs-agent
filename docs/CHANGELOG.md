# CHANGELOG — MGS Agent

Registro cronológico de mudanças operacionais na infraestrutura de agentes (Zeus, Atena) e integrações MGS.

## 2026-04-22

### Fix: compression threshold dos agentes Hermes (Zeus + Atena)

**Problema:** Warning técnico do Hermes vazava pro canal Discord da Atena, violando a regra do SOUL.md sobre "linguagem natural com humanos":

```
⚠ Compression model (claude-haiku-4-5-20251001) context is 200,000 tokens,
but the main model's compression threshold was 500,000 tokens...
```

**Causa:**
- Main model Sonnet 4.6 tem context = 1,000,000 tokens
- `compression.threshold` default = 0.50 (= 500k tokens) excedia o context do Haiku auxiliary (200k)
- Hermes auto-reduzia o threshold na primeira sessão e emitia o warning via `status_callback("lifecycle", ...)` → enviado direto pro Discord sem filtro

**Mudança aplicada em ambos config.yaml (Atena e Zeus):**

```yaml
compression:
  enabled: true
  threshold: 0.15        # era 0.5 — reduz pra 150k tokens (cabe em Haiku 200k)
  target_ratio: 0.2
  protect_last_n: 20
```

**Backups preservados:**
- `/root/.hermes/profiles/atena/config.yaml.bak_warnings`
- `/root/.hermes/profiles/zeus/config.yaml.bak_warnings`

**Cobertura:**
- ✅ Resolve o warning específico de compression auto-lower
- ⚠️ Outros lifecycle warnings futuros (ex: retry rate limit) ainda podem vazar pro Discord

**Pendente (Opção A — se necessário no futuro):**
Patch mínimo em `gateway/run.py:9482` (`_status_callback_sync`) adicionando filtro por env var `HERMES_SUPPRESS_LIFECYCLE=true`. Permitiria silenciar lifecycle messages na Atena (user-facing) mantendo-as ativas no Zeus (admin). ~5 linhas modificadas, reversível. Só aplicar se outro warning vazar.

**Upstream (reportável ao Hermes-Agent):**
Não existe flag nativa no Hermes pra suprimir mensagens de `status_callback("lifecycle", ...)` chegando no Discord. Issue candidato: `display.show_lifecycle_in_discord: false`.

### Context adicional (infra atual)

- Anthropic API: org `9642e8be-77aa-485f-8cdf-8c231d9015a7` em Tier 1 (30k ITPM, 8k OTPM, 50 RPM)
- Main model: claude-sonnet-4-6 em ambos profiles
- Auxiliary model: claude-haiku-4-5-20251001 (vision, title_generation, compression, etc)
- Sessões acumulam histórico — quando passam de 30k tokens, cada nova msg bate no rate limit Tier 1

## 2026-04-23

### Feature: Auto-commit watcher (inotify + systemd)

**Objetivo:** toda mudança em `/root/mgs-agent/` vira commit+push automático pro GitHub em ~10-15 segundos, sem intervenção manual.

**Peças:**
- `scripts/auto-commit-watcher.sh` — loop infinito com `inotifywait -r` + debounce de 10s; ao detectar mudança faz `git add -A && git commit -m "auto: <files>"`
- `/etc/systemd/system/mgs-autocommit.service` — wraps o script como service `Type=simple` + `Restart=on-failure` + `EnvironmentFile=/root/.hermes/.env` (pra hook de push ter `OP_SERVICE_ACCOUNT_TOKEN`)
- Push real é feito pelo post-commit hook **já existente** (token via 1P on-demand, nunca persistido)

**Exclusões** (pra não criar loop ou lixo):
- `.git/` — ignorar operações internas do git
- `.bak`, `.swp`, `.tmp` — editores/backups temporários
- `sessions/`, `/logs/` — fora do repo mas poderia ser tocado
- `node_modules`

**Defesa em profundidade — `.gitignore` reforçado antes de ativar:**
- `*credentials*`, `*secret*`, `*token*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`
- `.env.*`, `.git-credentials`
- `data/*.bak_*`, `*.bak`, `*.bak.*`

**Log:** `/root/mgs-agent/logs/auto-commit-watcher.log`

**Ops:**
- `systemctl status mgs-autocommit` — ver estado
- `systemctl restart mgs-autocommit` — após editar o script
- `systemctl stop mgs-autocommit` — pra pausar auto-commit temporariamente
- `journalctl -u mgs-autocommit -f` — stream de logs

**Teste de smoke** (validado em 2026-04-23 00:23):
- Edit em `docs/CHANGELOG.md` → watcher detectou → 10s depois commit `8dc6776 auto: docs/CHANGELOG.md` → hook 1P pushou em 1s → commit visível no GitHub

**Trade-offs conhecidos:**
- Cada edit pequena vira commit na history (ruído). Aceitável porque o git log serve como audit trail, não commit-graph curado.
- Debounce de 10s pode deixar passar 2 edits seguidas em 1 commit só (desejável) ou pode atrasar um commit mais do que o necessário (aceitável).
- Se o `OP_SERVICE_ACCOUNT_TOKEN` expirar, o commit ainda acontece mas o push falha silente (logado em `logs/auto-push.log`). Precisa monitorar.

