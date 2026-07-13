# Cross-agent session policy cutover

Use this procedure when a runtime/config change is already deployed, but a gate requires proof that a **new Atena/Ares Discord session** loaded the current policy. This is validation-only coordination, not production work.

## Preconditions

1. Reconcile the requested validation against live config, SOUL, audit, Git and gateway state. A pasted external analysis is a proposal, not proof.
2. Confirm Rodolfo authorized the validation turn. Do not infer authorization from the external analyst's wording alone.
3. Keep production, MEMORY/USER compaction and unrelated agent work blocked until the cutover gate passes.
4. Preserve any prior failed rollout/finalizer event. Later recovery never rewrites a failure into success.

## Create the validation sessions

1. Resolve each agent's current parent channel and bot ID from canonical config/Discord, rather than relying on remembered IDs.
2. Create one new, clearly named thread in each agent's own parent channel. Use 3–6 words, e.g. `Validação de Política Atena`.
3. Post from Zeus with a **direct mention of the destination bot**. With `DISCORD_ALLOW_BOTS=mentions`, an unmentioned bot message can be visible in Discord but ignored by the destination gateway.
4. Make the instruction validation-only and fail-closed:
   - no tools;
   - no memory/skill writes;
   - no production action;
   - one fixed acknowledgement response.
5. Validate transport in two stages:
   - Discord readback shows Zeus' message, the direct mention and the correct thread ID;
   - the destination agent replies in that thread.

## Canonical readback

Read the destination profile's `state.db` by exact thread ID. Require all of:

- a new Discord session exists for that thread;
- `system_prompt` contains the exact current policy sentence (`policy_in_prompt=true`);
- `tool_call_count=0` for the validation-only turn;
- Discord response came from the expected agent bot;
- no automatic-write receipt/audit event contradicts the no-write instruction.

Do not use the agent's acknowledgement alone as proof that its system prompt contains the policy. `state.db.system_prompt` is the proof.

If either agent is false or missing, leave the gate open, report the exact missing evidence and stop. A gateway restart does not itself create a new conversation session, so another restart does not solve a missing session cutover.

## Closing the rollout audit

When both agents pass:

1. Keep the original `gateway_restart_finalizer_failed` event immutable.
2. Append a **distinct** post-failure event such as `gateway_restart_revalidation_finished`; never synthesize a retroactive `gateway_restart_finalizer_finished`.
3. Record thread IDs, session IDs, `policy_in_prompt`, tool-call counts and the other runtime evidence under one correlation ID.
4. Emit a new REPORT-INFRA only because the runtime state changed from blocked to validated; the earlier blocked report remains valid history.
5. Read back the exact Discord embed and append its message ID to audit.
6. If the governance rule is already present live and in the mirror, record readback instead of duplicating text.

## Scheduler pitfall

A completed one-shot cron job does not wake up when a dependency later becomes healthy. Run the closure explicitly or schedule a new gated job; never tell Rodolfo that the old one-shot will resume by itself.
