# REC+P1 operation-time reporting and runner retry lessons — 2026-05-27

## Context

Rodolfo flagged a REC+P1 run where the final summary reported only the two successful runner durations (~2.5 min) even though the user-perceived Discord elapsed time was ~13 min from request to final summary.

## Durable rule

Final REC, P1 and REC+P1 summaries must report **tempo total da operação** as the main time metric.

This means elapsed time from the user request arriving to the final Discord summary being sent, including:

- failed runner attempts;
- retries;
- manual fact/competitor repair;
- image QA failures and regenerations;
- code/pipeline fixes made during the run;
- cleanup of orphan media;
- agent/tool overhead.

Runner-only duration may be used for diagnostics, but it must not replace the main final-summary time unless the user explicitly asks for runner timing only.

## Required implementation pattern

1. Capture an operation start timestamp immediately before beginning article execution.
2. Run REC/P1 pipelines normally.
3. At final-summary render time, pass elapsed wall-clock time into the renderer, e.g. `--operation-seconds <elapsed>` or `--started-at <timestamp>`.
4. Use the final-summary label `Tempo total da operação`, not `Tempo total dos runners`.

## Runner retry lessons from the same session

The Santander World Elite REC+P1 run exposed two pipeline gaps:

- Featured semantic audit failures can be stochastic. If the generated image fails because of CGI appearance, unnatural card placement, hidden logo, or missing realistic person, the runner should regenerate a bounded number of times instead of forcing the agent into manual reruns.
- P1 word-count expansion can stop slightly below the hard minimum. Keep deterministic filler available so the P1 body reaches the 900–1000 word gate without manual rewriting.

## Guardrails

- Bounded retries only; do not loop indefinitely.
- Preserve the semantic audit as a hard gate. Retrying is acceptable; bypassing the audit is not.
- If retries still fail, report a blocker instead of publishing with a weak image.
- Clean up media uploaded by failed attempts when it is safe and scoped to the current run.
