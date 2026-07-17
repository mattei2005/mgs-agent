# Hermes update 2026-07-05 — auto-restart collision + staged patch port

## Context

During a controlled MGS Hermes update from `7e8f50a14` to `a05b64d67`, Zeus first ported the canonical MGS runtime patch to upstream, then ran the controlled update with:

```bash
RESTORE_LOCAL_DIFFS=0 RESTART_GATEWAYS=0 STAMP=live-20260705-200622 \
  /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

The intended behavior was update-without-restart. The script itself did not call its `restart_if_requested` block, but the upstream `hermes update` command still performed its own gateway handling and attempted to drain/restart manual gateways for Ares/Atena/agente legado.

## Durable lessons

### 1. `RESTART_GATEWAYS=0` does not necessarily mean no gateway impact

In the current controlled script, `RESTART_GATEWAYS=0` only disables the script's explicit final `systemctl restart` block. If the script still calls official `hermes update`, upstream may independently drain/restart manual gateway profiles.

Operational consequence observed:

- Ares/Atena/agente legado were left in `activating/auto-restart`.
- Journals showed `Gateway already running (PID ...)`.
- Orphan replacement processes existed:
  - `python -m hermes_cli.main --profile ares gateway run --replace`
  - `python -m hermes_cli.main --profile atena gateway run --replace`
  - `python -m hermes_cli.main --profile legacy-agent gateway run --replace`
- Systemd units then looped because the orphan `--replace` processes held the gateway locks.

Recovery pattern:

```bash
for svc in atena-gateway.service ares-gateway.service legacy-agent-gateway.service; do
  systemctl stop "$svc" || true
done
sleep 2

for profile in atena ares legacy-agent; do
  pids=$(pgrep -f "hermes_cli.main --profile $profile gateway run --replace" || true)
  [ -n "$pids" ] && kill $pids || true
done
sleep 5

for profile in atena ares legacy-agent; do
  pids=$(pgrep -f "hermes_cli.main --profile $profile gateway run --replace" || true)
  [ -n "$pids" ] && kill -9 $pids || true
done

systemctl reset-failed atena-gateway.service ares-gateway.service legacy-agent-gateway.service || true
systemctl start ares-gateway.service legacy-agent-gateway.service atena-gateway.service
sleep 25
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service
```

Do not touch Zeus in this repair unless Zeus itself is impacted; Zeus should remain last and preferably via safe detached finalizer.

Future controlled-update implication:

- For a true no-restart/no-gateway-impact update, avoid the official `hermes update` path and use the manual no-restart playbook (`git pull --ff-only`, dependency refresh, patch guard, validation).
- If using official `hermes update`, treat it as potentially gateway-impacting even when script-level `RESTART_GATEWAYS=0`; immediately validate systemd state and orphan `--replace` processes before reporting success.

### 2. `git apply --3way` can stage the ported patch

When porting a canonical MGS patch in a temporary upstream worktree, `git apply --3way` may leave changes staged in the index. Generating the new patch with plain `git diff` can therefore produce an empty patch (`e3b0c442...`) even though the port succeeded.

Correct patch generation after `git apply --3way`:

```bash
git -C "$WT" diff --binary HEAD > "$NEW_PATCH"
[ -s "$NEW_PATCH" ] || { git -C "$WT" status --short; exit 1; }
git -C "$VERIFY_WT" apply --check "$NEW_PATCH"
```

`git diff --binary HEAD` captures both staged and unstaged changes relative to the worktree HEAD. Always validate the resulting patch is non-empty and applies cleanly to a fresh `origin/main` worktree.

## Validation shape used

- Port patch applied to `origin/main` with `git apply --3way`.
- MGS invariants present in `gateway/run.py`, `plugins/platforms/discord/adapter.py`, and `gateway/platforms/base.py`.
- `py_compile` passed for critical files.
- Targeted tests passed: `157 passed, 6 subtests passed`.
- New canonical patch `mgs-runtime-customizations-2026-07-05.patch` verified with `git apply --check` on fresh upstream.
- Post-update patch guard passed and gateways returned active after orphan repair.
