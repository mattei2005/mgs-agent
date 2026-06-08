# MGS repo dependency/tooling audit pattern

Use this when a `/root/mgs-agent` hardening pass reaches the dependency/tooling phase. Goal: reduce runtime risk without surprise package upgrades or pay-per-token regressions.

## Scope discovery

1. Enumerate dependency manifests, excluding `.git`, `node_modules`, caches and logs:
   - `package.json` / lockfiles
   - `requirements*.txt`, `pyproject.toml`, `Pipfile`, `poetry.lock`
   - Dockerfiles / compose files
2. Treat each dependency island independently. In the 2026-05 hardening pass, the only active npm package was `scripts/yoast-scorer`.
3. For Python, distinguish import availability from service reachability. A missing import is not actionable if the only service needing it is masked/inactive and the code path is deprecated.

## Safe npm checks

Run inside the package directory, not repo root:

```bash
npm audit --audit-level=moderate
npm outdated --json
npm test
```

If `npm test` is the default broken placeholder (`echo "Error: no test specified" && exit 1`), replace it with a deterministic syntax test rather than adding behavioral coverage on the fly. Example for a small JS tool:

```json
"test": "node -c yoast-scorer.js && node -c deprecated/yoast-score-updater.js"
```

Do not run `npm audit fix` or major version upgrades automatically during an infra hardening pass. Report and isolate those separately unless the user explicitly approves dependency churn.

## Legacy API / model-cost hardening

When finding old runtime code that imports Anthropic/FastAPI or uses pay-per-token model APIs:

1. Check service state first (`systemctl is-enabled`, `systemctl is-active`, ports/listeners, crontab refs).
2. If the service is already disabled/masked and policy forbids that provider by default, prefer a fail-closed stub over leaving runnable legacy code.
3. The stub should:
   - remove live imports for deprecated providers/frameworks;
   - return non-zero on direct execution;
   - emit a small machine-readable disabled/status JSON;
   - name the current replacement pipeline;
   - avoid reading credentials or `.env`.
4. Leave historical implementation recoverable via Git history; do not copy old provider code into comments.

Example status shape:

```json
{
  "status": "disabled",
  "service": "mgs-rec-api",
  "reason": "Anthropic/Claude API pay-per-token usage disabled by MGS policy",
  "replacement": "Atena content-generate-rec pipeline via GPT-5.5/OpenAI Codex OAuth",
  "timestamp": "..."
}
```

## Validation checklist

Before reporting success:

```bash
npm test
npm audit --audit-level=moderate
python3 -m py_compile api/generate-rec-api.py scripts/*.py skills/content-generate-rec-p1/scripts/*.py
python3 api/generate-rec-api.py   # should return rc=2 for disabled stub, not crash
scripts/monitor-cron-stale-logs.sh --dry-run
systemctl is-active zeus-gateway.service mgs-autocommit.service
systemctl is-enabled mgs-rec-api.service || true
systemctl is-active mgs-rec-api.service || true
git status -sb
```

Expected safe end state for the deprecated REC API pattern:

```text
mgs-rec-api.service: masked / inactive
api/generate-rec-api.py: disabled stub, rc=2 on direct execution
npm audit: 0 vulnerabilities for yoast-scorer
npm outdated: no actionable output
repo: clean and synced
```

## Reporting

Use a compact aligned block for Rodolfo:

```text
Área                     | Resultado
-------------------------|-------------------------------------------
npm                      | audit 0; outdated none; test sintático ok
legacy REC API           | stub disabled; serviço masked/inactive
Python compile           | ok
Git                      | limpo / main...origin/main
```

End with `Próximo passo pendente:`. If no critical item remains, say that explicitly and suggest a non-critical next block (release notes, historical-doc cleanup, ShellCheck) rather than inventing urgency.
