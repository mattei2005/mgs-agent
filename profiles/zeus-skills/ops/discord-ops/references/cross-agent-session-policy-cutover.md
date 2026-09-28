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
- the prompt resolved through `sessions.system_prompt_hash → system_prompts.hash` (fallback `sessions.system_prompt`) contains the exact current policy sentence (`policy_in_prompt=true`);
- `tool_call_count=0` for the validation-only turn;
- Discord response came from the expected agent bot;
- no automatic-write receipt/audit event contradicts the no-write instruction.

Do not use the agent's acknowledgement alone as proof that its system prompt contains the policy. The prompt resolved from `state.db` is the proof; an empty inline `sessions.system_prompt` is inconclusive when `system_prompt_hash` is populated.

If either agent is false or missing, leave the gate open, report the exact missing evidence and stop. A gateway restart does not itself create a new conversation session, so another restart does not solve a missing session cutover.

## Fleet-wide Discord route cutover

A new canary proves only that new sessions load the policy. It does not protect existing Discord threads whose routes still point to a session created with the old prompt.

1. After the new-session canary passes, enumerate every current Discord route in each target profile's `state.db` from `gateway_routing.entry_json`.
2. Resolve each route's prompt by joining `sessions.system_prompt_hash` to `system_prompts.hash`. On current Hermes, `sessions.system_prompt` can be empty because the prompt is content-addressed; use `COALESCE(system_prompts.prompt, sessions.system_prompt, '')` instead of treating an empty inline field as proof of absence.
3. Classify every route by exact policy sentence and checker path. Require counts for `policy_current`, `policy_stale` and stale routes with an active turn.
4. Never reset a route with an active turn. Stop and report the exact active blocker.
5. For an inactive stale Discord route, use the native `/new` command in that exact thread. For bot-to-bot coordination, directly mention the destination bot so `DISCORD_ALLOW_BOTS=mentions` admits the command; complete the command approval when that profile requires it.
6. Send one validation-only turn after the reset, then read back the new session ID, resolved prompt, checker marker and `tool_call_count=0`.
7. Do not close the rollout until every current Discord route for every target profile reports `policy_stale=0`. Preserve the old session rows as history; rotate routing rather than mutating a session's cached system prompt in place.

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
