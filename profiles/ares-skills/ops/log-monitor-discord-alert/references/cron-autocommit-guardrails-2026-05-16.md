# Cron / auto-commit guardrails — 2026-05-16

Contexto: auditoria completa do repo `/root/mgs-agent` encontrou um cron rodando com erro semântico sem acionar stale-log, e risco no auto-commit watcher por `git add .`.

## Técnicas validadas

### 1. `grep -c ... || echo 0` quebra aritmética Bash

`grep -c` imprime `0` quando não encontra match, mas sai com código 1. Se usado com `|| echo 0`, a variável vira `0\n0` e `[[ "$N" -eq 0 ]]` quebra com `syntax error in expression`.

Padrão correto:

```bash
COUNT=$(printf "%s" "$TEXT" | grep -c "PATTERN" || true)
COUNT="${COUNT:-0}"
```

Validação aplicada em `scripts/track-article-cost.sh`: execução real passou com `Pending publications: 0` e exit 0.

### 2. Stale-log monitor precisa scan semântico

Log fresco só prova que o cron rodou; não prova que rodou saudável. Acrescentar scan das últimas linhas para padrões específicos:

```python
SEMANTIC_ERROR_RE = re.compile(
    r'(syntax error|traceback|exception|fatal:|critical|erro crítico|error token|command not found|permission denied|no such file or directory)',
    re.I,
)
```

Evitar falso positivo de erro antigo: quando o log tem marcador de início (`start`, `iniciando`, `===`), analisar só o bloco da execução mais recente.

### 3. Auto-commit watcher: guardrail antes de `git add -A`

Risco: `git add .` ou `git add -A` pode commitar arquivo sensível criado fora do `.gitignore`.

Padrão validado:

```bash
SENSITIVE_PATH_REGEX='(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_ed25519|.*credential.*|.*secret.*|.*token.*|.*password.*|hosts\.yml|\.npmrc|\.pypirc)$'
SENSITIVE_CHANGES=$(git status --porcelain | awk '{print $2}' | grep -Ei "$SENSITIVE_PATH_REGEX" || true)
if [ -n "$SENSITIVE_CHANGES" ]; then
  log "BLOQUEADO: arquivo sensível detectado; commit automático abortado"
  printf '%s\n' "$SENSITIVE_CHANGES" | while IFS= read -r f; do log "  sensitive: $f"; done
  continue
fi

git add -A -- .
```

Pitfall validado: não misturar `git add -A -- . ':!.env' ...` quando `.env` já está ignorado; o Git pode abortar com “paths are ignored by one of your .gitignore files: .env”. O guardrail via `git status --porcelain` + `.gitignore` é mais estável.

### 4. Validação pós-hardening

Checklist mínimo após tocar monitores/autocommit:

```bash
bash -n scripts/track-article-cost.sh scripts/auto-commit-watcher.sh scripts/monitor-cron-stale-logs.sh
scripts/track-article-cost.sh
scripts/monitor-cron-stale-logs.sh --dry-run
systemctl restart mgs-autocommit.service
systemctl status mgs-autocommit.service --no-pager --lines=10
git status -sb
```

Regenerar inventário quando scripts/cron mudam:

```bash
scripts/infra-discovery.sh >> logs/infra-discovery.log 2>&1
scripts/cron-control-plane.py --write-doc >> logs/cron-control-plane.log 2>&1
```
