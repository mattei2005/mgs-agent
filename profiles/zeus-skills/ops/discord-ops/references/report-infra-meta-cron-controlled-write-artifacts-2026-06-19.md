# REPORT-INFRA — Meta cron/control-write artifacts (Ares) — 2026-06-19

## When this applies

Use this reference when processing `[REPORT-INFRA]` from Ares or another MGS agent for Meta Ads automations that include a mix of:

- repo scripts under `/root/mgs-agent/scripts/`;
- profile-local Hermes cron wrappers under `/root/.hermes/profiles/<agent>/scripts/`;
- Hermes cron jobs in another profile’s `cron/jobs.json`;
- controlled-write or read-only audit JSON/CSV/image directories under `/root/mgs-agent/data/.../audit/`;
- Discord posting helpers that use another agent’s bot token/channel permissions.

## Lessons captured

### 1. Profile-local wrappers are runtime infra, not git artifacts

For wrappers like `/root/.hermes/profiles/ares/scripts/*.sh`:

1. Validate with `bash -n`.
2. Record `path`, `size_bytes`, `modified_at`, `sha256`, `profile`, `git_tracked=false` in `infra-inventory.json`.
3. Do **not** try to `git add` the wrapper; commit only `infra-inventory.json` plus versioned repo artifacts.
4. If the wrapper is attached to a Hermes cron, verify the cron entry still points to that script.

### 2. Cron removal should be represented explicitly

When a Hermes cron is removed from `~/.hermes/profiles/<agent>/cron/jobs.json`, do not delete its inventory history. Update the existing `crons[]` entry:

- `enabled=false`
- `state="removed"`
- `removed_at=<timestamp>`
- `validation.cron_absent_from_jobs_json=true`
- keep prior schedule/script/name for auditability.

This preserves why a one-shot/obsolete automation disappeared.

### 3. Large audit directories need a manifest-level entry

For read-only audit directories containing many files (CSV/JSON/JPG thumbnails/contact sheets), register the directory as a single `data_files[]` entry when individual file entries would be noisy:

- `path` ending with `/`
- `size_bytes` = sum of files
- `sha256_manifest` = SHA256 of a stable manifest such as `relative_path<TAB>size<TAB>sha256` per file
- `counts` for the business validation (e.g. campaigns/adsets/ads/creatives/thumbnails, CSV line counts)

Still validate structured files with `json.tool`/CSV row counts and scan text files for token-like secrets.

### 4. Controlled-write audits require final-state validation

For approved Meta controlled-write scripts, validation is not just `py_compile`:

- dry-run audit JSON parses and states `dry_run=true`;
- real execution audit is captured if execution started;
- final live/audit validation records business state, e.g. target campaign count, budgets, start range, `issues_count=0`;
- cleanup audits explicitly list deleted temporary campaigns and verification status.

If execution is still running in another session, record the observable handle conservatively (Hermes process id if visible, OS `ps` observation if not) and use the audit file as the durable evidence.

### 5. Cross-profile Discord token validation pitfall

When validating Discord permissions for another agent’s bot, do **not** use `os.environ.setdefault('DISCORD_BOT_TOKEN', value)` if Zeus already has its own token in the environment. Force the token from the target profile `.env` for the validation subprocess:

```python
if key == 'DISCORD_BOT_TOKEN':
    os.environ[key] = value_from_target_profile_env
```

Otherwise the check may accidentally validate Zeus’ bot instead of Ares/agente legado/etc. Report only bot ID and permission booleans; never print the token.

## Commit hygiene

Stage surgically:

- repo script/data/audit files that are meant to be versioned;
- `data/infra-inventory.json`;
- not profile-local wrappers, not runtime process state, not unrelated pending Ares/agente legado/Zeus files.

Final ACK remains the normal canonical form: `✅ Registrado. Inventário atualizado (commit XXXX).`
