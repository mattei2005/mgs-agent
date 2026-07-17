# MGS Hostinger post-migration finalization — autocommit/Git cleanup

Use this reference after a full MGS/Hermes VPS migration when gateways and crons are already live but Git/auto-commit/cleanup still need to be made production-clean.

## Durable lesson

A migration is not operationally complete just because Zeus/Atena/Ares/agente legado are active on the new VPS. The final validation must also prove:

- `mgs-autocommit.service` exists, is `active` and `enabled` on the target.
- `inotifywait` is installed and the watcher can detect changes.
- `.git/hooks/post-commit` pushes `HEAD:main` successfully.
- `HEAD == origin/main`, branch is `main`, and `git status --short` is `0`.
- Runtime/staging artifacts from migration are cleaned or explicitly ignored.
- A real create/delete smoke test produces auto-commit and auto-push both ways.

## Recovery pattern used on Hostinger

1. Check state:

```bash
cd /root/mgs-agent
git rev-parse --abbrev-ref HEAD
git fetch --quiet origin main
git rev-parse --short HEAD
git rev-parse --short origin/main
git status --short | wc -l
command -v inotifywait || true
test -f /etc/systemd/system/mgs-autocommit.service && echo service-file=yes || echo service-file=no
```

2. Install watcher dependency if missing:

```bash
apt-get update -qq
apt-get install -y -qq inotify-tools
```

3. Create/recreate the service:

```ini
[Unit]
Description=MGS Agent Auto-Commit Watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/mgs-agent
EnvironmentFile=-/root/mgs-agent/.env
ExecStart=/root/mgs-agent/scripts/auto-commit-watcher.sh
Restart=on-failure
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

Then:

```bash
bash -n /root/mgs-agent/scripts/auto-commit-watcher.sh
systemctl daemon-reload
systemctl enable --now mgs-autocommit.service
systemctl is-active mgs-autocommit.service
systemctl is-enabled mgs-autocommit.service
```

4. Before committing migration leftovers, pause the watcher and preserve rescue evidence:

```bash
systemctl stop mgs-autocommit.service
TS=$(date +%Y%m%d-%H%M%S)
BK=/root/mgs-agent-rescue/git-rescue-$TS
mkdir -p "$BK"
git status --porcelain=v1 > "$BK/status.txt"
git diff > "$BK/working-tree.diff" || true
git diff --cached > "$BK/index.diff" || true
```

5. Secret-scan changed files before staging. Do not print secrets; report only counts/paths if needed.

6. Commit/push in controlled chunks. Validate:

```bash
git fetch --quiet origin main
git rev-parse --short HEAD
git rev-parse --short origin/main
git status --short | wc -l
```

7. Restart watcher and run a real smoke test:

```bash
systemctl start mgs-autocommit.service
TEST="data/autocommit-smoke-$(date +%Y%m%d-%H%M%S).txt"
echo "smoke $(date -Iseconds)" > "$TEST"
# wait until dirty=0 and HEAD==origin/main
rm -f "$TEST"
# wait again until dirty=0 and HEAD==origin/main
```

Expected evidence:

- create commit pushed;
- delete commit pushed;
- `mgs-autocommit.service=active/enabled`;
- `HEAD == origin/main`;
- dirty count `0`.

## Ignore/cleanup guidance

Do not auto-version browser profiles, token debug dumps, or transient restart finalizers. Add or preserve ignores like:

```gitignore
data/browser-profiles/
data/ares/meta-ads/audit/token-debug-*.json
data/mgs-gateway-restart-finalizer-*.sh
```

If migration staging exists under `/root/migration-backups` after validated cutover, remove it to reclaim disk. In the Hostinger finalization, removing staging reduced disk use from about 26% to 18%.

## Pitfalls

- `post-commit` hook existing is not enough; without `mgs-autocommit.service`, dirty work never turns into commits.
- `mgs-autocommit.service active` is not enough; prove end-to-end with create/delete auto-commit + auto-push.
- Sensitive filename guardrails can false-positive on documentation names like `secret-wrappers`. Prefer a narrow allowlist for safe docs/tools after content scan, not disabling the guardrail.
- Do not rely on GitHub page recency by eye; compare `HEAD`, `origin/main`, and optionally `git ls-remote origin refs/heads/main`.
- Use `git add -A -- <filtered paths>` rather than broad staging if ignored runtime directories may contain tracked history or sensitive files.
