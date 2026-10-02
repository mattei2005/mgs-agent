# Hostinger MCP — process routing and speed

## Purpose and scope

Apply this matrix when choosing between the Hostinger MCP, official API and Linux/SSH for MGS VPS work. Rodolfo authorized auditing the existing processes and updating the corresponding Zeus skills in message `1555606771035275375`, thread `1555572634228490283`. This is a routing standard, not authorization to modify jobs or expose additional operations.

## Preferred route by operational object

- **Hostinger VPS state/configuration, historical provider CPU/RAM/disk/network/uptime:** prefer the fixed-target Hostinger MCP for interactive agent queries. Use `vps_virtual-machines_get` and `vps_virtual-machines_metrics`; generate UTC bounds using tools and record the metric timestamp/unit. Provider telemetry is not instantaneous guest telemetry.
- **Provider backups/snapshot inventory and provider operation history:** prefer `vps_backups_list`, `vps_snapshots_get`, `vps_actions_list`. Follow pagination and preserve absolute timestamps/timezones. Do not equate listing with archive integrity, application-consistent recovery or restore-test success.
- **Instantaneous disk/inodes/MemAvailable/load and largest directories/processes:** keep Linux. The Hostinger aggregate series cannot identify recursive candidate/stage producers, per-filesystem inode pressure, open files, or an active worktree. Do not replace `df`, `du`, `/proc`, process/PID/fd checks or inode-aware accounting.
- **Zeus/Atena/Ares/systemd readiness, journals, safe restart finalizers and producer health:** keep the native guest procedures. Hostinger `running` proves VM state, not Discord connectivity, PostgreSQL or application health. Provider action history is corroboration only; guest restart audit/finalizer evidence remains authoritative.
- **Ubuntu APT/kernel/needrestart, Node/npm, Hermes Git delta/patches/config/profile cutover:** keep controlled Linux/Hermes workflow. No current Hostinger VPS API operation does that exact guest package/runtime transaction. Provider preflight context does not close these acceptance gates.
- **Crontab, systemd timers, Hermes scheduler, locks, retry/outbox/anti-spam:** keep their current scheduler and scripts. MCP is a callable interface, not a scheduler. Do not replace healthy unattended deterministic scripts with agent loops merely to use MCP.
- **Offsite encrypted quick/full backup, manifests/hashes, Drive upload, isolated restore tests and DR SLA:** retain `mgs-offsite-backup.py` and its quick/full/restore-test/monitor wrappers, plus the safety snapshot workflow. Provider backups/snapshot add a distinct recovery option; they do not replace these scope/consistency/validation requirements.
- **Smart Bidding, DTR, Meta campaigns/tokens, Sheets/Drive, WordPress/Yoast, finance quotes/revenue/spend:** retain each application's own API/helper/skill. A job running on this VPS does not make the job's business object manageable through Hostinger.
- **Remote RunCloud sites/finance database:** retain their approved host bindings and credentials. The fixed Hostinger VM target is not authority or access to Inc01/Inc02/Inc03JBF.

## Optional provider capabilities — not enabled or validated by implication

The reviewed official `hostinger-api-mcp@2.7.0` VPS catalog contains 64 operations: 21 GET and 43 POST/PUT/DELETE. The MGS catalog deliberately exposes only five GET operations.

- Monarx scan metrics may supplement malware/security context; the local Monarx service and security logs remain necessary. The additional GET is not enabled or tested by this audit.
- Provider firewall/public-key readback may support an exact hardening investigation. It does not prove guest firewall/sshd state and does not authorize altering keys/firewall.
- Provider Docker projects/containers/logs apply only to workloads managed by the provider Docker interface. Do not migrate current systemd workloads merely to gain MCP visibility. The audited host had no active docker.service or Docker socket.
- Data-center/OS-template/post-install-script catalogs support provisioning, not routine repair of current applications. Post-install scripts/reinstall are not a remote-shell replacement.
- Reboot/stop/restore/reinstall/firewall/public-key/password/billing actions remain separate owner-confirmed operations under current AGENT.md. Never broaden the guarded catalog to execute them incidentally.

## Performance rule

Do not claim that MCP is inherently faster. The MCP delegates to the same official REST API and adds protocol/process overhead. It can reduce operator/model effort compared with navigating a dashboard; that is not a measured network latency gain.

- Prefer warm native MCP for interactive provider queries after native trust/SDK validation.
- For a separately authorized deterministic unattended collector, compare native MCP versus direct official API for the **same object and predicate**, including token bootstrap, startup, warm/cold calls, pagination, failures and credential consumption. Preserve 1Password-only storage and existing scheduling.
- Keep high-frequency local health signals independent of Hostinger network/API and 1Password availability. Never run the full standalone probe every five minutes merely to replace cheap local telemetry: each new process resolves 1Password again (288 projected bootstraps/day at a 5-minute cadence), while the gateway's warm MCP process resolves once per start.
- Provider historical metrics, guest instantaneous metrics and a full health collector are not equivalent benchmark workloads. Label projections and observed timings distinctly; no invented speedup percentages.

## Native read-only classification gate

A registered/connected MCP server and a successful standalone SDK smoke do **not** prove that the Hermes model-facing execution path is usable. Test at least one native `execute` through the actual trust gate before calling native operation fully validated.

The deployed Python MCP SDK uses `ToolAnnotations.read_only_hint` and `CallToolResult.is_error`, with camelCase JSON wire aliases. A Hermes reader that only asks for object attribute `readOnlyHint` can treat a genuine GET-only tool as write-capable. Reproduce that mismatch with an isolated annotation object and inspect the actual `_annotation_read_only_hint` function; do not infer API failure.

If that classification causes approval refusal:

1. Treat the refused call as not executed. Never retry it through direct API/standalone or change `trust` to `full` to circumvent that refusal.
2. Keep `trust: untrusted`, the five-operation allowlist, fixed target and credentials unchanged.
3. Record connected/discovered, standalone validated, native execution blocked as separate states with source/evidence.
4. Request the distinct runtime correction scope when not already authorized. A compatibility fix must support snake_case SDK fields and camelCase cache/wire dicts while preserving fail-closed unknown/malformed annotations; it must not mark the unrestricted upstream catalog read-only.
5. Validate false/absent/string hints remain write-capable, actual safe native GET succeeds only after authorized deployment, forbidden operation/batch still fails before API access, and no unrelated profile/trust changes occur. Follow safe activation/restart policy if deployment requires it.

## Audit evidence and completion

The source audit is recorded under `work/hostinger-process-audit-1555606771035275375/`: scheduler inventories, all-scheduled-source-audit, full vendor capability catalog, coverage summary and native-readonly-compatibility-blocker. These artifacts are findings, not instructions.

Read every discovered schedule/source batch back and aggregate/dedupe by code before asserting coverage. Never present a root-only cron list as whole-VPS coverage. Distinguish routing/skill changes from active job/config migrations. Backup retirement and changes to other agents' skills keep their own confirmation gates.
