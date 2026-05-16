# Post-update validation workflow

Use after every `hermes update`, even when `hermes --version` says "Up to date" immediately afterward.

## Required checks

```bash
repo=/root/.hermes/hermes-agent

# 1. Confirm no newer upstream commit landed during/after the update
hermes --version 2>&1 | sed -n '1,25p'
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD
git -C "$repo" rev-parse --short origin/main
git -C "$repo" rev-list --count HEAD..origin/main
git -C "$repo" rev-list --count origin/main..HEAD
git -C "$repo" diff --name-only HEAD..origin/main | wc -l

# 2. Confirm local patch footprint is still present
git -C "$repo" status --short
git -C "$repo" diff --stat

# 3. Confirm local patches would still apply cleanly to upstream
patchfile=/tmp/mgs-local-hermes-current.patch
tmp=/tmp/hermes-update-conflict-check-$(date +%s)
git -C "$repo" diff > "$patchfile"
git -C "$repo" worktree add --detach "$tmp" origin/main
if git -C "$tmp" apply --check "$patchfile"; then
  echo APPLY_CHECK=OK
else
  echo APPLY_CHECK=FAIL
fi
git -C "$repo" worktree remove --force "$tmp" || rm -rf "$tmp"

# 4. Syntax/import smoke on patched files
py="$repo/venv/bin/python"
"$py" -m py_compile \
  "$repo/gateway/platforms/discord.py" \
  "$repo/gateway/run.py" \
  "$repo/tools/discord_tool.py"
"$py" - <<'PY'
import importlib
for m in ['gateway.platforms.discord','gateway.run','tools.discord_tool']:
    importlib.import_module(m)
    print(f'{m}=OK')
PY

# 5. Service health
systemctl is-active zeus-gateway.service atena-gateway.service
systemctl show zeus-gateway.service atena-gateway.service \
  -p MainPID -p ActiveState -p SubState -p NRestarts -p MemoryCurrent -p MemoryPeak --no-pager
journalctl -u zeus-gateway.service -u atena-gateway.service \
  --since '10 minutes ago' --no-pager \
  | grep -Ei 'traceback|exception|critical|oom|killed|failed with result|main process exited' || true
```

## Targeted test suite for Discord/gateway patch safety

Production Discord env vars can contaminate unit tests that use fake channel IDs. For hermetic pytest runs, explicitly unset channel allow/ignore/no-thread filters:

```bash
cd /root/.hermes/hermes-agent
env -u DISCORD_ALLOWED_CHANNELS -u DISCORD_IGNORED_CHANNELS -u DISCORD_NO_THREAD_CHANNELS \
  ./venv/bin/python -m pytest -q \
    tests/gateway/test_discord_imports.py \
    tests/gateway/test_discord_send.py \
    tests/gateway/test_discord_reply_mode.py \
    tests/gateway/test_discord_thread_persistence.py \
    tests/gateway/test_discord_slash_commands.py \
    tests/gateway/test_discord_component_auth.py \
    tests/gateway/test_update_streaming.py \
    tests/tools/test_discord_tool.py \
    tests/tools/test_send_message_tool.py
```

Interpretation:
- `HEAD == origin/main`, `behind_count=0`, `diff_files=0` → no update still pending.
- `APPLY_CHECK=OK` → local patch is structurally compatible with current upstream.
- `py_compile` + import smoke OK → patched files are syntactically/import-safe.
- Targeted pytest passing → Discord/gateway/send-message surfaces most likely affected by MGS patches are not broken.
- Service active + no post-stabilization critical logs → operationally healthy.

## Reporting expectation

Report success only after update check, service status, local patch verification, and targeted tests. Include any residual infra risk separately (example: zero swap causing OOM risk), but do not call the update validated until the checks above pass.