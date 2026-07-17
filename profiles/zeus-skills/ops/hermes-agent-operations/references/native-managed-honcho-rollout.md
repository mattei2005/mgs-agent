# Native managed Honcho rollout runbook

Use this reference when enabling or repairing the native Hermes Honcho memory provider across multiple agent profiles. Honcho is a longitudinal context/user-model layer; MGS OS, operational databases, audit logs, skills and minimal always-on USER/MEMORY remain canonical.

## 1. Authorization and preflight

1. Confirm managed versus self-hosted and whether operational conversation persistence is authorized.
2. Treat introducing/reusing a production API key as a credential-impacting operation and run the required critical confirmation gate.
3. Inventory each profile independently. Do not infer native activation from a working wrapper, API key, health script or old `honcho` stanza.
4. Verify:
   - native plugin exists;
   - `honcho-ai` is installed in the active Hermes venv;
   - profile config and its repository mirror agree before editing;
   - gateway/service state is known;
   - protected backup and rollback path exist.

## 2. Secret-safe configuration

- Store `HONCHO_API_KEY` in each profile's protected `.env` (`0600`).
- Keep profile-local `honcho.json` non-secret and `0600`; reject keys named `apiKey`, `oauth`, `token`, `secret` or `password` in this file.
- Never write the key to Git, command arguments, documentation, reports or Discord.
- Verify the configured value against 1Password by boolean equality only; never print either value.
- Do not relay raw `hermes honcho status` output in Discord because the current command reveals an API-key suffix. Prefer `hermes memory status` plus an internal boolean `key_present` check.

## 3. Recommended profile topology

Use one shared workspace when cross-agent user continuity is desired, while keeping a distinct AI peer per agent:

- workspace: shared corporate workspace;
- AI peer: stable profile/agent name;
- user peer alias: stable human identity (for Discord, map the canonical user ID);
- unknown users: prefix runtime IDs to avoid collisions;
- `saveMessages=true` only when explicitly authorized;
- bounded `contextTokens`;
- hybrid recall for automatic context plus explicit tools;
- async writes, conservative dialectic cadence and shallow initial depth.

Provider quirk: on the deployed native plugin, startup reads common cadence settings from `cfg.raw`. Put `contextCadence` and `dialecticCadence` at the JSON root as well as in any host block whose effective settings must remain self-documenting.

## 4. Sequential rollout

For each agent, in blast-radius order:

1. Back up config, `.env`, USER/MEMORY and existing Honcho config.
2. Add/replace exactly one `HONCHO_API_KEY` line atomically.
3. Write the non-secret `honcho.json` atomically.
4. Set `memory.provider: honcho` with the native scalar config writer.
5. Synchronize the existing config mirror only after a pre-write equality check.
6. Validate file modes, provider status and secret absence.
7. Run a native provider read-only profile canary.
8. Run a full Hermes-agent canary that calls `honcho_profile` without creating conclusions.
9. Proceed to the next agent only after the current one passes or its unrelated blocker is isolated and reported.

Do not use a manual copilot success as proof of native provider activation.

## 5. Canary layers

A complete rollout distinguishes these checks:

- **Config check:** provider resolves to `honcho`; host block and workspace are correct.
- **Dependency check:** `honcho-ai` imports in the active venv.
- **Native provider check:** initialization and read-only `honcho_profile` return normally.
- **Full agent check:** a fresh Hermes agent sees and successfully calls the native tool.
- **Gateway check:** live gateway remains healthy; fresh sessions load new tool schemas.
- **Continuity check:** a non-sensitive conclusion can be recovered in a later isolated session when a write canary is warranted.

Existing sessions are not guaranteed to gain new provider tools retroactively. Prefer a fresh session/reset; do not restart active gateways merely to retrofit the current conversation.

## 6. USER/MEMORY semantics

- Honcho models the user from persisted conversations.
- The current native `on_memory_write` hook mirrors only successful `add` operations targeting `user` into a Honcho conclusion.
- USER `replace`/`remove` and MEMORY writes are not mirrored by that hook.
- This is not bidirectional file synchronization. Exact always-on policy remains in USER/MEMORY; longitudinal context and semantic conclusions belong in Honcho.
- Keep the 90% capacity monitor as a residual safety net rather than making direct file compaction the primary architecture.

## 7. Short-lived process shutdown pitfall

Hybrid mode can create daemon workers for:

- background session initialization;
- dialectic prewarm;
- context prefetch;
- async message writing.

A successful CLI answer followed by `SIGABRT` is evidence of lifecycle leakage, not a failed Honcho tool call. The durable fix is to:

1. drain session init before reading late-created worker references;
2. join dialectic/prefetch/sync workers;
3. call the manager's lifecycle `shutdown()`, not `flush_all()` alone;
4. track and join context-prefetch workers;
5. signal and join the async writer;
6. add regression tests for late prefetch creation, manager shutdown invocation and tracked context-worker drain;
7. rerun provider tests and a real short-lived full-agent canary.

Preserve runtime fixes as a reviewed patch artifact with a post-update guard instead of relying on an untracked edit inside the Hermes checkout.

## 8. Closure

Before declaring success:

- verify all profile configs and mirrors;
- verify `.env`/`honcho.json` modes and exact key presence without disclosure;
- scan changed repository files for the exact secret value and require zero hits;
- run provider tests and monitored health checks;
- record per-agent canary outcomes and unrelated blockers separately;
- update institutional decision/capability, checkpoint, inventory and audit;
- publish one canonical REPORT-INFRA with readback;
- verify auto-commit/auto-push rather than manually pushing unless explicitly requested;
- retain the protected rollback backup.
