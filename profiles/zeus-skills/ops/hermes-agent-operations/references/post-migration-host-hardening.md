# Post-migration host hardening

Use after a VPS cutover when the old host is decommissioned, credentials appear “missing” inside tools, or a gateway experienced an apparent OOM.

## 1. Separate OOM evidence from shutdown cleanup

1. Read the kernel journal for the exact victim, timestamp, RSS and PID (`Out of memory: Killed process ...`).
2. Correlate with the gateway journal and command history.
3. Do not misidentify later `systemd` cgroup cleanup (`State stop-sigterm timed out. Killing.`) as the original OOM victim.
4. Inspect service memory peak, cgroup limits, host RAM/swap, filesystem capacity, existing `/etc/fstab` swap entries and swappiness overrides.
5. Treat swap as resilience, not the root-cause fix. Also harden the workload: streaming search, directory exclusions, per-file size caps and bounded output.

For an approved 4 GiB swapfile on ext4: backup `/etc/fstab`, create `/swapfile`, mode 0600, `mkswap`, `swapon`, add one idempotent fstab entry and set a conservative value such as `vm.swappiness=10` in `/etc/sysctl.d/`. Validate `swapon --show`, `free`, `sysctl`, file metadata and `findmnt --verify`. Any `/etc` edit follows the Critical Subset confirmation.

## 2. Distinguish service credentials from sandbox passthrough

A messaging gateway can have its bot token correctly loaded from the profile `.env` while `terminal`/`execute_code` intentionally strips it. Verify without printing values:

- systemd `EnvironmentFiles` path;
- presence of the key name in each profile `.env`;
- gateway connection/readiness;
- whether the Hermes provider/messaging credential blocklist contains the variable.

Do not “fix” protected messaging credentials by forcing them through `terminal.env_passthrough`. Hermes rejects this to preserve sandbox credential scrubbing. Remove ineffective passthrough entries, use native Discord tools for reads/admin, and use a canonical poster that loads the profile `.env` internally for scripted delivery. Never recover a token from `/proc/<gateway-pid>/environ` as a workaround.

## 3. Retired IP/domain sweep

Search and classify independently:

1. tracked repository content (`git grep`);
2. untracked repo files;
3. live profile configs, skills, scripts and cron stores;
4. root crontab and `/etc/cron*`;
5. systemd units;
6. SSH config and both plain/hashed known-host entries (`ssh-keygen -F <host> -f <known_hosts>`);
7. external firewall/Fail2Ban allowlists referenced by operational procedures;
8. historical audit logs, imported conversations, browser state and backups.

Remove or replace retired endpoints only on executable/config/operational surfaces. Preserve append-only audit/import/backup evidence, but label current docs so the host is never described as active or standby. Add a guard that fails if the retired endpoint reappears outside explicitly allowlisted historical paths.

If a retired public IP was previously whitelisted on downstream servers, perform a read-only live firewall audit first. Removing the old rule or adding the new egress IP is a separate Critical Subset firewall action requiring explicit confirmation and readback.

## Reporting

For each finding, report: confirmed source, operational vs historical classification, proposed action, validation, rollback and exact approval gate. Do not bundle swap, profile config cleanup, repository cleanup and firewall modification into one approval.