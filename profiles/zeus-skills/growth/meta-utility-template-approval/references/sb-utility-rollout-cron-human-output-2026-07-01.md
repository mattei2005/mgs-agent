# SB Utility rollout cron human output — 2026-07-01

## Trigger

Rodolfo saw a script-only Hermes cron delivery like this in Discord:

```json
{
  "status": "OK",
  "changed": true,
  "changed_count": 1,
  "errors": [],
  "log": "/root/mgs-agent/logs/sb-utility-rollout-20260701-020102.json",
  "tracker": "/root/mgs-agent/data/sb-utility-rollout-tracker.json"
}
```

Correction: “Vc precisa melhorar o visual humano desse cron aqui”.

## Lesson

For Hermes `no_agent=true` jobs, stdout is delivered verbatim. JSON is good for logs and parsers, but bad as the user-facing Discord body. The script must render a human operations summary before printing.

## Output contract

- No changes and no errors: print nothing. Empty stdout keeps the cron silent.
- Changes: print a short human summary with changed count, per-template before/after counts, bad-row replacement count when non-zero, current active-target distribution, and log path.
- Errors: print a short attention summary with affected templates and error excerpts.
- Keep raw machine payloads in the run log JSON.

Recommended shape:

```text
SB Utility Rollout — atualizado

Templates atualizados: 1
- Template Name: 10 → 20 mensagens | ruins trocadas: 2

Estado atual: 48 em 20 | 11 em 10
Log: /root/mgs-agent/logs/sb-utility-rollout-YYYYMMDD-HHMMSS.json
```

Error shape:

```text
SB Utility Rollout — atenção

Templates atualizados: 0

Erros: 1
- Template Name: POST 500: [short excerpt]

Estado atual: 48 em 20 | 11 em 10
Log: /root/mgs-agent/logs/sb-utility-rollout-YYYYMMDD-HHMMSS.json
Status: WARN
```

## Implementation pattern

In the rollout manager, return rich structured data from `run_due()` for internal use:

- `changed_results`: list of changed template result objects;
- `errors`: list of error objects;
- `active_target_counts`: current tracker distribution;
- `log`: path to full JSON log.

Then call a formatter only in the CLI path for `run-due`:

```python
result = asyncio.run(run_due(force=False))
msg = format_run_due_message(result)
if msg:
    print(msg)
```

Do not remove the JSON log. The log remains the audit trail; stdout is the executive notification.

## Verification pattern

Use an ad-hoc `/tmp/hermes-verify-*.py` script that imports the manager under the same venv used by the cron (for this workflow, `/tmp/sb-venv/bin/python`) and asserts:

- changed results render the human header and per-template lines;
- no-op result returns an empty string;
- error result renders the attention header, error lines and WARN status;
- JSON markers such as `"status"` do not appear in the user-facing message.

Compile the modified script and remove the temporary verifier after it passes.
