# Post-rollout memory capacity and pending reconciliation

Use this procedure after Honcho or another semantic memory provider is enabled, and whenever Rodolfo asks “o que ainda falta?”.

## 1. Separate the memory layers

- Honcho handles longitudinal conversation context, user modeling, semantic retrieval and conclusions.
- USER/MEMORY remains the small always-active cache for exact preferences and invariants.
- Enabling Honcho does not shrink existing USER/MEMORY or prove that a capacity watchdog exists.
- Never describe a custom LLM compactor as the primary architecture once native semantic memory is active.

## 2. Verify residual protection in runtime

Do not infer an active 90% monitor from policy, documentation or a checkpoint saying that it “remains”. Verify all three runtime planes:

1. root/system cron entries;
2. Hermes scheduled jobs;
3. an installed MGS monitor script and its latest state/readback.

Also read the live USER/MEMORY character counts against the configured limits. Report exact count, percentage and remaining characters to the threshold. Runtime wins over documentation.

If no monitor exists, classify it explicitly as a real pending item rather than silently treating the policy as implemented.

## 3. Residual design after Honcho

Keep only a read-only capacity watchdog as normal automation:

- trigger at `>=90%`;
- create a protected backup before any proposed mutation;
- alert in `#limites-90` with current size, target and proposal metadata;
- never mutate USER/MEMORY from the watchdog;
- never run an autonomous recurring LLM compactor as the main memory mechanism.

A controlled compaction remains an exception path and requires Rodolfo’s explicit authorization. When authorized:

1. process one entry at a time;
2. require JSON/contract-valid output;
3. require all literals such as IDs, paths, hashes, URLs and canonical names to survive exactly;
4. discard an invalid transformation and preserve the original entry;
5. accumulate only validated replacements;
6. write once atomically after the target headroom is reached (normally `<=85%`);
7. perform readback, reverse hash/checksum and live/mirror validation;
8. on any failure, preserve the original file and alert without partial mutation.

## 4. Answering “what remains?”

Reconcile before answering:

1. inspect the direct source/thread for each named operation;
2. inspect runtime and audit/inventory;
3. inspect the latest checkpoint;
4. treat old backlog files as secondary until reconciled.

Classify every item into one of four buckets:

- **Waiting on Rodolfo** — explicit authorization or external manual action is still required.
- **Already authorized and in progress elsewhere** — report it, but state that Rodolfo has no further action.
- **Normal monitoring / awaiting future scope** — not an operational pending item.
- **Stale backlog** — disclose age/drift and do not present its raw count as current truth.

Important pitfall: do not present a model-auth blocker for an agent that has already been intentionally decommissioned as a repair pending. Reconcile decommission/archive work first. Likewise, do not reopen a resolved credential cutover from an older checkpoint when the direct thread and later audit show completion.

## 5. Executive response shape

Keep the answer short and decision-oriented:

- what still requires action;
- what is already running and needs nothing from Rodolfo;
- what is only backlog/monitoring;
- the single recommended next action.

If a runtime readback contradicts an earlier statement, own the correction directly and update the canonical checkpoint during the same task.
