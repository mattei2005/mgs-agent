# Pending REPORT-INFRA monitor — attribution and explanation

Use this reference when a Discord alert claims that a skill, script, cron, config, or data artifact is “sem REPORT-INFRA”, “pending report”, or later “resolved”. The goal is to explain what was actually pending without treating the alert title as proof.

## Core distinction

A monitor’s **display label** is not necessarily the condition it tests. Before saying a REPORT-INFRA was absent, inspect the monitor implementation and identify its real predicate.

Common predicates include:

- artifact absent from `data/infra-inventory.json`;
- state entry present in a pending/alerted map;
- missing audit record;
- missing Discord report;
- filesystem/inventory mismatch.

If the code checks only inventory membership, report the finding as **inventory registration missing or transiently unreadable**, not as confirmed absence of a Discord REPORT-INFRA.

## Investigation sequence

Follow the MGS attribution gate and reduce evidence at the source:

1. `logs/events-audit.jsonl` — look for creation, modification, inventory update, report, and resolver events.
2. `data/infra-inventory.json` — inspect the exact collection and key the monitor reads, not just a broad text search.
3. `#alerts-infra` — inspect the original alert/resolution and any earlier REPORT-INFRA when Discord history is available.
4. Git — inspect the artifact history and inventory history separately.
5. `session_search` — use only for historical intent or missing local context.
6. Inspect the monitor script, state file, and bounded log window to reconstruct the exact predicate and timeline.

For large or nested JSON inventories, parse recursively and print only matching JSON paths. A plain line search may miss a valid entry because of large-file truncation, formatting, or tool limits.

## Commit attribution guard

Never assume a commit shown in a “resolved” embed added the named artifact. Inspect how the monitor selects commit evidence.

A weak implementation such as:

`git log -1 -- data/infra-inventory.json`

returns the latest commit that touched the inventory globally. It does **not** prove that the commit added or fixed the specific skill. Validate the named entry in the commit and its parent, or inspect the path-specific history.

Classify commit evidence precisely:

- **specific fix commit** — diff adds/repairs the named entry;
- **inventory snapshot containing the entry** — entry exists, but commit changed unrelated inventory content;
- **unrelated latest inventory commit** — embed attribution is misleading;
- **unproven** — history or source unavailable.

## Transient mismatch diagnosis

When consecutive monitor runs show `OK → PENDENTE → RESOLVIDO`, but Git before and after already contains the entry:

- treat it as a transient inventory read/write mismatch or concurrent rewrite until a writer is attributed;
- do not invent the writer or call it an anomaly prematurely;
- reconcile audit, inventory, REPORT-INFRA, Git, and sessions before classification;
- state the remaining gap plainly if the exact writer cannot be proven.

## Current-state validation

Before saying the issue is closed, verify all applicable layers:

- live artifact exists;
- versioned mirror exists when one is expected;
- exact inventory collection contains the correct name/path;
- monitor state moved from `alerted` to `resolved`;
- next bounded monitor run reports no pending item;
- REPORT-INFRA existence is described separately unless the monitor truly verifies Discord/audit evidence.

## Executive explanation format

Answer in this order:

1. what the artifact is and why it exists;
2. what the monitor actually detected;
3. the alert/resolution timeline;
4. current validated state;
5. any misleading label or commit attribution;
6. operational impact and the one remaining evidence gap, if any.

Do not confuse an infrastructure bookkeeping alert with a pending business/content task. Do not say “sem REPORT-INFRA confirmado” when only inventory absence was measured.