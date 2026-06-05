# Discord gateway restart and cross-agent routing coordination

Use this reference when changing Zeus/Atena gateway routing, restart behavior, or Discord auto-thread settings during an active operational test.

## Principle

Do not combine routing patch, gateway restart, scheduled self-check, and live content benchmark in the same moment unless the user explicitly accepts interruption risk. When the user is actively testing Atena, stabilize routing first, validate once, then let content tests proceed.

## Safe sequence for Zeus routing changes

1. Inspect current Zeus/Atena Discord routing config.
2. Patch config/runtime so Zeus can read shared channels but does not answer Atena content threads unless explicitly mentioned.
3. Validate syntax/config before restart.
4. Restart only the affected service.
5. Verify service state with `systemctl show` / `is-active` after the restart completes.
6. Avoid scheduling a cron/self-check from the same bot being restarted unless there is no other safe way; a self-check can collide with gateway drain/retry behavior and confuse the user.
7. Tell the user when it is safe to open new Atena content threads.

## Expected Zeus/Atena routing target

```text
Zeus admin channel          | Zeus may respond without mention
Atena content channel       | Zeus may read/analyze, but only responds with explicit @Zeus
Atena content threads       | Zeus stays silent unless explicitly mentioned
Atena bot                   | handles content requests normally
```

## Pitfall observed

If Zeus has Atena's content channel in `allowed_channels` and `require_mention=false`, Zeus may auto-thread or respond to normal Atena requests, creating duplicate operational threads. Fix by constraining free-response behavior to Zeus admin channel and requiring mention elsewhere.

## Communication rule after user frustration

If the user reports that the system is freezing/travando, stop optional automation immediately, check service state, remove pending scheduled checks if present, and report only concrete status plus the next safe action. Do not continue explaining long background context before stabilizing the service.

## Restart interruption recovery expectation

If a gateway restart/SIGTERM interrupts an active turn, the system should return to the same Discord thread after reconnect and post a deterministic recovery/closure message. Rodolfo should not have to prompt Zeus to continue after a restart that Zeus initiated or coordinated.

Use `references/gateway-restart-recovery-checkpoint.md` for the implementation pattern: write a profile-local checkpoint before shutdown notification, recover it on startup after Discord reconnect, send one idempotent status message, and mark delivered to avoid duplicates. Keep this recovery deterministic; do not launch a heavy LLM cron/self-check from the same restarting bot unless explicitly approved.
