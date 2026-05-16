# Cron SSH hardening — monitors using RunCloud jump host

Validated during MGS repo audit/hardening on 2026-05-16.

## Problem class

Some cron monitors used `expect` + password auth through the RunCloud jump host and had:

```text
scp -o StrictHostKeyChecking=no -J zeus@46.4.95.117 ...
ssh -o StrictHostKeyChecking=no -J zeus@46.4.95.117 ...
```

This avoids prompts but disables host-key verification and leaves predictable local `/tmp` helper scripts when combined with static temp paths.

## Safer pattern used

For existing password/expect flows where a full SSH-key migration is too risky for the same patch:

```bash
TMP_DIR="$(mktemp -d /tmp/monitor-name.XXXXXX)"
REMOTE_SCRIPT="/tmp/monitor_name_$$.sh"
KNOWN_HOSTS_FILE="/root/.ssh/known_hosts_mgs"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=${KNOWN_HOSTS_FILE}"
mkdir -p /root/.ssh
touch "$KNOWN_HOSTS_FILE"
chmod 600 "$KNOWN_HOSTS_FILE"
chmod 700 "$TMP_DIR"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT
```

Expect wrapper takes SSH options as an argv parameter rather than hardcoding insecure options:

```tcl
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set local_script [lindex $argv 2]
set remote_script [lindex $argv 3]
set ssh_opts [lindex $argv 4]
set timeout 30
spawn sh -c "scp $ssh_opts -J zeus@46.4.95.117 \"$local_script\" zeus@162.55.28.178:\"$remote_script\""
```

SSH execution pattern:

```tcl
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set remote_script [lindex $argv 2]
set ssh_opts [lindex $argv 3]
set timeout 120
spawn sh -c "ssh $ssh_opts -J zeus@46.4.95.117 zeus@162.55.28.178"
# ... password expects ...
send "bash $remote_script; rm -f $remote_script\r"
```

## Validation checklist

1. `bash -n scripts/monitor-name.sh`
2. Run the monitor once manually with output redirected to its normal log.
3. Verify expected remote data marker appears / monitor completes successfully.
4. Verify `/root/.ssh/known_hosts_mgs` exists and is non-empty after first connection.
5. Verify local temp dir cleanup occurs via trap.
6. Verify `git status` clean after auto-commit watcher settles.
7. If monitor is normally silent unless degraded, confirm the manual run does not post Discord unnecessarily.

## Important pitfalls

- Do not replace password/expect with permanent SSH keys unless Rodolfo explicitly approves the security model. Prefer incremental hardening first.
- `accept-new` is safer than `no`, but it still trusts the first observed key. For highest assurance, pre-seed known_hosts with verified fingerprints.
- Keep local temp files under `mktemp -d` with `chmod 700`; do not use static `/tmp/_name.exp`.
- Use unique remote paths such as `/tmp/name_$$.sh` and remove the remote script after execution.
- Pass SSH options as arguments to expect wrappers. Hardcoding inside heredocs makes future audits harder and tends to leave insecure flags behind.
