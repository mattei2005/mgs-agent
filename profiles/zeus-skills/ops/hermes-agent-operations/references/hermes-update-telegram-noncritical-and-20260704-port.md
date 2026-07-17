# Hermes update MGS — Telegram non-critical + 2026-07-04 patch port

Session context: Rodolfo asked to continue the Hermes update process silently, preserving MGS standards. He explicitly corrected scope: Telegram is not used by MGS and should not consume backup/control/test effort during Hermes updates.

## Durable workflow correction

Telegram is not an MGS-critical surface. Do not block Hermes updates on Telegram-specific tests, backups, or patch porting.

Still validate Telegram-adjacent code only when the changed code path is shared with the MGS-critical surfaces:

- Discord gateway behavior
- Zeus/Atena/Ares/agente legado systemd gateways
- restart safe/auto-resume/checkpoint behavior
- GPT-5.5/OpenAI-Codex and zero Claude default
- MGS profile config/SOUL/auth presence
- REPORT-INFRA inline/no-auto-thread behavior
- Discord output cleanliness and context non-actionability

## 2026-07-04 validated port pattern

Live state before port:

```text
Hermes live      efd87a154
Origin/main      09693cd3a
Behind           637 commits
Gateways         Zeus/Atena/Ares/agente legado active
```

Precheck had shown drift in the old canonical patch:

```text
mgs-runtime-customizations-2026-06-30.patch  DRIFT
```

Correct action taken before any live update/restart:

1. Create detached worktree from `origin/main`.
2. Build a critical MGS patch from the live diff while excluding Telegram-dedicated test file.
3. Apply with `git apply --3way` in the worktree.
4. Resolve conflicts by preserving both upstream improvements and MGS invariants.
5. Run `py_compile` on critical files.
6. Run targeted Discord/restart tests, not Telegram tests as a blocker.
7. Generate a new canonical patch and promote it in the guard/precheck script.
8. Run `PRECHECK_ONLY=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh` before any live update.

Result:

```text
Patch                       /root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-07-04.patch
Patch clean apply           OK against origin/main
Targeted tests              157 passed + 6 subtests
Precheck controlled          OK
MGS invariants missing       0
Live update                  not run
Gateway restart              not run
```

## Conflict resolution lessons

### `gateway/run.py`

Conflict was between upstream `platform_connect_timeout` env bridge and MGS `auto_attach_local_files` env bridge. Correct resolution: keep both. The upstream bridge remains an env-var override path; MGS auto-attach remains config-driven safety gate.

### `plugins/platforms/discord/adapter.py` — channel context

Conflict was between upstream read-only context header and MGS unverified-sender warning. Correct resolution: keep the read-only/non-actionable header and also keep the unverified warning when applicable. For no reply/no unverified cases, preserve the compact legacy shape expected by tests: header + direct lines, without adding `[Recent channel messages]` unless needed for multi-block context.

### `plugins/platforms/discord/adapter.py` — auto-thread creation

Conflict was between upstream direct/fallback create_thread flow and MGS retry/remember-title behavior. Correct resolution: preserve retry loop and call `_remember_auto_thread_initial_title(thread, thread_name)` on both direct and fallback thread creation paths.

## Test selection rule after Rodolfo correction

Do not spend time porting/running Telegram-specific tests as mandatory evidence for MGS updates. Use targeted tests that validate MGS surfaces, e.g.:

```bash
PYTHONPATH="$wt" /root/.hermes/hermes-agent/venv/bin/python -m pytest -q \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_restart_resume_pending.py
```

If a changed shared function is covered only by a Telegram-named test file, prefer moving/adding the relevant assertion into a Discord/gateway test instead of making Telegram part of the MGS critical path.

## Reporting style correction

When Rodolfo asks to execute silently, do not narrate each phase. Work until one of these terminal states:

- success with evidence;
- failure with cause and next action;
- real production/restart decision required;
- blocker that cannot be resolved safely.

Final report should be concise and include whether live update/restart happened. In the 2026-07-04 port, only precheck/patch promotion happened; no live update and no restart.