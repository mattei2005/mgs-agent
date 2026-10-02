# Hostinger MCP — audit of current VPS processes

## Authority and bounded scope

Rodolfo requested analysis of current processes versus Hostinger MCP and corresponding skill updates in message `1555606771035275375`, thread `1555572634228490283`. Scope: Hostinger VPS `1767265`, its Linux schedulers, Zeus/Atena/Ares schedule entrypoints and the installed official VPS catalog. No jobs, alert cadence, production runtime, live config, credentials, permission/trust scope, other profiles' skills or critical operations were changed.

## Coverage, read back and aggregated in code

- 51 active root-crontab entries.
- 36 stored Hermes jobs across Zeus/Atena/Ares; 13 enabled (Zeus11/Ares2/Atena0).
- 10 system-cron entries, 11 OS periodic-script files and 18 systemd timers.
- Only root has a Unix user crontab; no default-profile jobs file present.
- 63 unique scheduled source files inspected, including profile wrappers and their resolved script paths. Infrastructure DR wrappers additionally traced to mgs-offsite-backup.py implementation.
- All63 mapped: 48 keep their current route with no Hostinger equivalent; 15 guest/DR infrastructure entrypoints retain local behavior, with provider-side context supplementary. These are source files, not63 independent business workflows.
- Full installed official Hostinger2.7.0 VPS catalog reviewed:64 operations,21GET and43mutating. FiveGET currently enabled by the fixed-target local adapter; extra vendor operations are not enabled/validated by implication.

Evidence: `work/hostinger-process-audit-1555606771035275375/coverage-summary.json`, scheduler inventories, all-scheduled-source-audit.json and vendor-vps-capabilities.json. Every discovered collection was persisted before aggregation; no root-only inventory presented as whole-VPS coverage.

## Operational conclusion

MCP is not universally faster or better. It is a callable interface over the official Hostinger API, not a scheduler or a guest shell. It improves interactive provider queries compared with navigating the panel, but no measured universal API latency advantage exists.

### Prefer Hostinger MCP for interactive provider queries once native execution gate is repaired/validated

- VM identity/state/configuration.
- Historical provider CPU/RAM/disk/network/uptime.
- Hostinger backup and current-snapshot metadata.
- Provider operation history.

These capabilities exist in the current five-operation GET-only catalog. Backups/actions paginate; provider timestamps and measurement semantics remain explicit. Listing does not validate restoration.

### Keep current Linux/application/DR route

- monitor-vps-health.py: instantaneous disk/inodes/MemAvailable/load, APT metadata, backup-directory size, service expected-state/restart reconciliation and top-consumer/PID classification are not reproduced by provider aggregate metrics.
- monitor-service-restarts.sh and Hermes watchdog/update monitors: systemd/journals, Git delta/local patches, provider/auth/profile readiness are guest runtime predicates.
- APT/kernel/needrestart/Node/npm and safe Hermes activation: keep exact controlled transaction and separate gates; provider update/security flags cannot close guest validation.
- Crontab/systemd/Hermes schedules, retry/locks/outbox/delivery: preserve healthy deterministic schedulers, not agent loops to make work look MCP-native.
- Encrypted offsite quick/full backup, manifest/hash checks, isolated restore-test, DR SLA and operational safety snapshot: retain existing tools and recovery requirements. Provider snapshots can complement, not automatically replace, these artifacts or permit deleting archives.
- SmartBidding/DTR/Meta/WordPress/Yoast/finance/Drive/Sheets retain domain APIs/helpers. Hosting a job on the VPS does not make its business object part of Hostinger API. Remote RunCloud production hosts remain separate bindings.

### Optional future reads, not activated

Monarx scan metrics can supplement local Monarx/security logs. Provider firewall/public-key reads may support a later exact hardening audit. Docker project/container/log endpoints are relevant only to provider-managed Docker workloads; this host had inactive docker.service and no Docker socket, so no workload migration justified. Template/data-center/post-install catalogs support provisioning rather than routine cron/guest repair. Mutating provider operations retain exact owner confirmation gates.

## Performance and dependency observations

- Five read-only local instantaneous telemetry samples had median approximately0.05ms for disk/meminfo/uptime/load reads. This is not a full-health-collector measurement and not semantically equivalent to provider historical series.
- A full MCP-vs-direct-API network benchmark was not completed because the native execute gate refused a read-only call. No denied call was retried through another interface.
- Launching the standalone MCP probe on every five-minute tick would project288new1Password bootstrap reads/day, rather than the gateway's one-per-process-start token resolution. This is a projection, not observed rate-limit telemetry. No such job was created.
- For a separately authorized deterministic future provider collector, compare direct official API and warm/cold MCP on equivalent predicates, including startup, pagination, credentials and failure behavior. Do not degrade local alert independence from Hostinger/1Password.

## Newly proven native execution blocker — prior validation boundary corrected

- Native MCP search returned all five guarded operations.
- A native `execute` VM-details request was refused by Hermes as write-capable on the untrusted server. Tool explicitly reported that the request was NOT run; no actual provider mutation occurred.
- Cause reproduced without network retry: deployed SDK ToolAnnotations has Python attribute `read_only_hint=True` and serializes wire `readOnlyHint=true`; legacy Python attribute `readOnlyHint` is absent. Runtime `tools/mcp_tool_registration.py::_annotation_read_only_hint` reads only that old object attribute (or wire dict key), returning false for the genuine modern SDK object.
- Earlier successful standalone SDK smoke and gateway registration were real, but did not exercise this native approval layer. They do not prove native execute usable without an approval gate. This report supersedes that readiness interpretation, not the actual installation/GET-only server proof.
- trust remains untrusted; no switch to full, no annotation trick, no direct/standalone reroute of the refused request, no extra operation, no runtime-code edit or gateway restart.
- Recommended next scope: owner-approved narrow Hermes annotation-reader compatibility fix supporting SDK snake_case and wire/cache camelCase, fail-closed for missing/false/string hints; validate native safe GET and forbidden operations, deploy via safe runtime activation if needed. This correction is beyond the requested skill/routing edits and awaits Rodolfo.

## Skill changes and readback

Only Zeus canonical skills changed; five files across four skills, mirrored byte-for-byte:

1. hostinger-vps-operations: routing pack and mandatory native trust/SDK gate, performance/dependency reasoning and operation matrix.
2. vps-maintenance-and-backup-governance: provider preflight route without replacing guest maintenance/DR acceptance.
3. log-monitor-discord-alert: local-health/cron/DR preservation and provider telemetry separation.
4. hermes-agent-operations, web-tooling reference: connection versus native-execution validation and no bypass of refusal.

No living cron/monitor was migrated. This is a completed audit and procedure update with a separately identified native compatibility blocker, not a completed native-runtime correction. Infrastructure receipt and exact silent REPORT-INFRA message are recorded with readback in this operation's closure-result.json.
