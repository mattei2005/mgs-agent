# REPORT-INFRA processing playbook — Zeus

Use this when another MGS agent reports infra creation/modification/removal in `#alerts-infra`.

## Goal

Turn a `[REPORT-INFRA]` into auditable state, not a discussion. Validate the evidence, update `/root/mgs-agent/data/infra-inventory.json` when needed, append audit trail, commit only the relevant tracked files, then reply with the canonical 1-line ACK.

## Standard flow

1. Validate the exact artifacts named in the report.
   - Python scripts: `python3 -m py_compile <script>`.
   - Bash wrappers: `bash -n <wrapper>`.
   - JSON data/policy/operation files: `python3 -m json.tool <file> >/dev/null`.
   - Hashes: `sha256sum <paths>` and compare to the report.
   - Hermes cron jobs: inspect the owning profile cron DB, usually `/root/.hermes/profiles/<agent>/cron/jobs.json`, and confirm `id`, `enabled`, `state`, `script`, `no_agent`, `deliver`, `schedule`, `repeat`, and `next_run_at`.
   - Hermes controlled update reports: validate live Hermes `HEAD == origin/main`, `behind=0`, patch guard output, `py_compile`, targeted pytest log, gateway `systemctl is-active`, and the named report directory. Do not require `final-report.md` if the report directory has the concrete evidence files; read `run.log`, `post-revisions.txt`, `post-hermes-version.txt`, patch-guard logs and pytest logs directly. Treat `config.yaml` backup/live differences caused by upstream schema/default migration as WARN, not FAIL, only when critical MGS invariants remain (`openai-codex`, `gpt-5.5`, compression threshold/auth/SOUL intact). If live `infra-inventory.json` already has unrelated drift, use the surgical commit-from-HEAD pattern below so the REPORT-INFRA commit contains only the validated update/script entries.
   - WordPress plugin/config reports: validate the real rendered path, not only source lint or raw browser fixtures. If a plugin embeds JSON config in `<script type="application/json">`, inspect/render the actual WP output; `esc_html($json)` can entity-encode quotes and break `JSON.parse(script.textContent)` even when direct fixtures pass.
   - For WordPress plugin admin UIs, separate public-route proof from admin proof. Unauthenticated `curl` to `/wp-admin/admin.php?page=...` can return login/404 and is not proof of admin success; validate admin claims only with an authenticated browser/session or credentialed API. Public routes still need live DOM checks (`JSON.parse`, first UI state rendered, non-empty body, UTM passthrough) before ACK.
2. Update `/root/mgs-agent/data/infra-inventory.json` for every durable infra artifact:
   - `scripts[]`: include scripts/wrappers, including profile-local wrappers outside the repo such as `/root/.hermes/profiles/ares/scripts/*.sh`; store `path`, `size_bytes`, `modified_at`, and `sha256`.
   - `data_files[]`: store `path`, `size_bytes`, `md5`, `modified_at`, and `sha256` for policy/operation/state/report JSONs.
   - `crons[]`: add/update a structured entry for Hermes cron jobs with profile, id, schedule, script, `no_agent`, `deliver`, state, repeat, and intended local-time note when timezone conversion matters.
   - `skills_hermes.<agent>[]`: for MGS-specific profile skills, include active `skill_md`, versioned `versioned_skill_md`, `sha256`, `versioned_sha256`, category, and modified time.
3. Preserve inventory order where practical. Avoid regenerating/sorting large inventory sections if it creates noisy diffs unrelated to the report.
4. Append one compact JSONL entry to `/root/mgs-agent/logs/events-audit.jsonl` with: `report_infra_processed`, source agent, action/type, paths, validation, and whether inventory was updated. The audit log may be local-only; do not force it into git if ignored.
5. Commit only tracked/relevant repo files for the reported infra: inventory, new/modified repo scripts/data/skills. Do not include unrelated dirty files from other agents/threads.
   - If `infra-inventory.json` is already dirty with unrelated discovery drift, do a surgical inventory commit from `HEAD`: write `git show HEAD:data/infra-inventory.json` to a temp JSON, apply only the report's inventory entry to that temp file, validate it with `python3 -m json.tool`, then stage that exact blob with `git hash-object -w /tmp/<file>.json` + `git update-index --cacheinfo 100644,<blob>,data/infra-inventory.json`. This preserves the live working-tree drift while keeping the commit report-only.
6. Final response must be exactly one of the canonical ACK shapes, max two lines:
   - `✅ Registrado.`
   - `✅ Registrado. Inventário atualizado (commit XXXX).`
   - `❌ Erro ao processar: {motivo}`

## Pitfalls

- A report can name profile-local files outside `/root/mgs-agent`; validate and inventory them, but they cannot be committed directly. Commit the versioned mirror if one exists.
- `cron job <id>` may be a Hermes profile cron, not Linux crontab. Check the profile `cron/jobs.json` before using `crontab -l`.
- If a report includes timezone intent (example: “00:30 Europe/Madrid”), verify the stored cron expression and record the intended local-time note in inventory to prevent future confusion.
- If a helper grep/search returns no inventory entry, that is not failure; add the missing entry.
- Do not summarize all validation details back to Rodolfo in the final ACK. Validation belongs in inventory/audit/commit; the chat response stays short.
