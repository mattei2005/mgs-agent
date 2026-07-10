### Gateway routing/restart incident reference

When correcting routing between Zeus/Atena, avoiding duplicate threads, restarting a gateway during an active conversation, or designing recovery after restart interruption, see:
- `references/discord-gateway-routing-and-restart-incident-2026-05-18.md`
- `references/gateway-restart-coordination.md`
- `references/gateway-restart-recovery-checkpoint.md`

Rule: Zeus can keep read access to Atena's channel, but must not free-respond/auto-thread there without explicit @Zeus. During benchmark or maintenance, do not combine patch + restart + cron/self-check from the bot being restarted; stabilize the service first, then validate. If a restart interrupts an active turn, recovery must be deterministic and return to the same thread with status/next-step so Rodolfo does not need to prompt “continua”.

