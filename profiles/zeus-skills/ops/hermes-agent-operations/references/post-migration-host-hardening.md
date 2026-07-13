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

## 4. Reconcile parallel sessions before declaring an anomaly

Zeus sessions in different Discord threads do not share live conversational context. A legitimate action from another thread can therefore look unauthorized locally. Before using the word “anomaly”:

1. identify the file, commit, timestamp and apparent actor;
2. inspect the direct sources first: `events-audit.jsonl`, infra inventory, REPORT-INFRA and Git history/diff;
3. search Zeus session history by commit, path or operation for the originating authorization;
4. classify matched evidence as a reconciled concurrent action, ambiguous evidence as an unattributed concurrent change, and only unlogged/conflicting evidence as a governance anomaly.

For every mutable infra operation, prefer a shared correlation tuple in audit/reporting: `operation_id`, origin thread/session, approval message ID, actor and resulting commit. Before saying “nothing changed,” account for background review/forks triggered by the turn and limit the claim to foreground activity while they may still act.

## 5. Preserve YAML types when cleaning Hermes config

`hermes config set` converts booleans and numbers, but a value such as `'[]'` can be stored as the string `"[]"` rather than an empty list. After any structured config write, validate the parsed YAML type and live-versus-versioned equality. If the CLI cannot express the required list/dict type, use Hermes' atomic YAML writer with an actual Python list/dict, then read back the parsed value; never accept a visually plausible scalar as equivalent.

## 6. Harden SSH only after reconciling the firewall control plane

A local `firewall-cmd --permanent` readback is not enough when RunCloud or another control plane owns the zone. Before changing global `22/tcp`, inspect the control-plane firewall model and prove that a future deploy/reconcile will not recreate retired rules or overwrite the intended whitelist. Treat unresolved control-plane ownership as a blocker, not a caveat.

For a lockout-safe SSH whitelist rollout:

1. inventory every legitimate source and confirm which egress addresses are actually stable;
2. never allow a broad residential ISP range for a dynamic admin IP—establish access through a stable bastion/management host or WireGuard/Tailscale first;
3. change one server at a time, keep two SSH sessions open and verify provider/emergency-console access;
4. arm a time-bounded automatic rollback that restores global SSH before restricting anything;
5. add approved `/32` rules in runtime and permanent state, then prove fresh authorized connections;
6. remove global `22/tcp` in runtime only, run positive and negative connection tests, and remove it permanently only after every check passes;
7. cancel the rollback only after runtime, permanent config, nftables, Fail2Ban, control-plane state and fresh SSH readbacks agree.

Do not start discovery or implementation merely because the design was approved. A suspended rollout remains suspended until the owner explicitly authorizes the read-only discovery phase, and firewall mutations retain their separate Critical Subset confirmation.

## Reporting

For each finding, report: confirmed source, operational vs historical classification, proposed action, validation, rollback and exact approval gate. Do not bundle swap, profile config cleanup, repository cleanup and firewall modification into one approval.