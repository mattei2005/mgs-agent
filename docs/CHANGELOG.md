# CHANGELOG — MGS Agent

Registro cronológico de mudanças operacionais na infraestrutura de agentes (Zeus, Atena) e integrações MGS.

## 2026-04-27

### Cleanup operacional + segurança curl-auth + organização do repo

**Pacote ALTA — Segurança e correções:**
- Migrados 6/6 scripts WP-facing para helper `wp_curl_auth` (curl -K tempfile chmod 600). Senha não aparece mais em `ps aux` ou `/proc/*/cmdline`. Migrações novas hoje: `check-slug-conflict.sh` (commit 682b8d9) + `test-connection.sh`. Ver `docs/security/migration-curl-auth-20260427.md`.
- `update-yoast-scores.sh` movido para `scripts/deprecated/` (usava `wp yoast index --object-id` que não existe em Yoast v27.x; substituto: `skills/content-generate-rec/scripts/yoast-score-post.sh`).
- CLAUDE.md atualizado: 2 notas de Technical Debt marcadas RESOLVED 2026-04-27, Phase 1 marcada ✅ COMPLETE, "How to Resume This Session" reescrita.
- AGENT.md ↔ CLAUDE.md: confirmado escopos diferentes (AGENT.md = operacional dos agentes; CLAUDE.md = pipeline técnico). Convivem.

**Pacote LIMPEZA SEGURA — Housekeeping:**
- Deletado `agent-learned-skills/` (2 SKILLs duplicatas; versões canônicas em `profiles/zeus-skills/ops/`).
- Deletado `data/cleanup-backup-20260427-121204/` (13 arquivos lixo, 7 com nomes shell-vazados commitados por engano).
- Deletado lixo binário em `data/`: `debug-card-aib.png`, `debug-featured-aib.png` (~2 MB), `post-aib-rec.json`. Referência em CLAUDE.md L62 atualizada.
- Deletados 4 backups `.bak` antigos sem dependência (`authorized-users.json.bak_clean`, `authorized-users.json.bak_pre_v3`, `sites.json.bak_fincgriffin_*`, `pending-reports-state.json.bak_*`). Mantido `yoast-readability-eggbev-snapshots.json` como fail-safe do health monitor.
- Deletados 3 backups Yoast snapshots de teste do dia (`*.bak2`, `*.bak-test`, `*.bak-20260427013411`).
- Movidos para `scripts/deprecated/`: `monitor-rec-readability.sh` + `monitor-yoast-readability-eggbev.sh` (substituídos por `monitor-yoast-health-eggbev.sh` em 26/04).
- Deletado `package.json` órfão da raiz (yoast-scorer tem o seu próprio).

**Pacote MÉDIA — Operacional:**
- SKILL `mgs-infra-inventory` atualizada com números reais (skills_hermes: atena=78, zeus=87) — antes estava "atena=77, zeus=80" (data 24/04, desatualizado).
- Criado `docs/site-counting.md` documentando os números: 32 sites MGS oficiais (sites.md), 27 em RunCloud, 5 em SFTP (openzed/cliquet/fincgriffin), 107 webapps RunCloud total (80 não-MGS).
- Cron diário 5 AM adicionado para `infra-discovery.sh` (antes só rodava manual). Total crons ativos: 7 → 8.

**Impacto:**
- ~2 MB liberados do repo
- 22 arquivos deletados, 3 movidos pra deprecated, 5+ arquivos atualizados
- Repo significativamente mais limpo → Zeus/Atena consomem menos tokens consultando inventários

---

## 2026-04-26

### openzed.com EXIT CHECKLIST 100% concluído

- WP File Manager removido pelo Zeus em openzed.com (commit 5a0476a).
- Post-mortem do incidente: SOUL Zeus atualizado com regra absoluta sobre base64 inventado (causa raiz: Atena gerou b64 falso ao invés de processar arquivo real). Commits a589ce1, 686b765.
- Case study L2 adicionado ao SOUL Zeus.

### `monitor-yoast-health-eggbev.sh` substitui readability monitor

- Novo monitor unificado SEO + Readability (substitui `monitor-yoast-readability-eggbev.sh` e `monitor-rec-readability.sh`).
- Cron diário 10 AM EST (servidor America/New_York, DST automático).
- Snapshot novo: `data/yoast-health-eggbev-snapshots.json` (formato unificado, max 90 snapshots ~3 meses).

---

## 2026-04-25

### sync-souls.sh estendido para versionar skills MGS-específicas

- Commit 2791736: `feat(sync): extend sync-souls to version MGS-specific skills`.
- Antes: só `souls` (atena-soul.md, zeus-soul.md) sincronizavam */5min.
- Agora: também sincroniza skills MGS-específicas em `profiles/{atena,zeus}-skills/` ↔ `/root/.hermes/profiles/{atena,zeus}/skills/`.
- Permite versionar Git skills internas MGS (ex: `mgs-infra-inventory`, `wp-rest-mu-plugin-deploy`).

### `monitor-auto-push.sh` ativado

- Commit dc26b8f: detecta falhas no auto-push (commits sem `push OK`), threshold consecutive_failures >= 3.
- State em `data/auto-push-monitor.json`. Anti-spam 2h, janela de 60min.
- Cron */15min.

---

## 2026-04-24

### Yoast scorer real (Node.js + @yoastseo) integrado ao pipeline

- Commit 7f19c4e: `feat(yoast): add scorer Node.js lib + yoast-score-post.sh shell integration`.
- Antes: scores Yoast eram calculados aproximadamente.
- Agora: scores reais via `@yoast/yoastseo` v3.6 (mesma engine do plugin Yoast).
- Tested: post 62008 (AIB Visa Gold) → SEO 84/green, Readability 90/green ✅.
- Step 12 adicionado em `skills/content-generate-rec/SKILL.md` (uso pós-publish).

### SOUL Atena: novas regras (3 + 2)

- Commit fae4411: 3 regras de 2026-04-24 (image delete + button color + yoast grey).
- Commit be8ffad: 2 regras adicionais (verificar existência física antes de operar + reportar mudanças de infra ao Zeus).

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

