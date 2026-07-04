# Discord normal responses vs REPORT-INFRA — 2026-07-03

## Trigger

Rodolfo explicitly corrected Zeus for putting a raw `[REPORT-INFRA]` block inside a normal operational reply/thread. He said this had been happening repeatedly.

## Durable rule

Do not append or embed `[REPORT-INFRA]` blocks in normal Rodolfo-facing replies, validation threads, or operational summaries.

Normal reply to Rodolfo should contain only:

- the operational result;
- concise blockers/risks;
- recommended next action when needed.

REPORT-INFRA belongs only in the proper infra reporting flow/channel/thread when actually required by the MGS infra-report policy. Do not use it as a footer or proof block in the same message as the operational answer.

## Practical pattern

Wrong:

```text
[operational answer]

[REPORT-INFRA] ...
Ação: modificada
Tipo: skill/data
...
```

Right:

```text
[operational answer only]
```

Then, if infra reporting is required, process/report through the dedicated infra workflow separately, not as part of the user-facing answer.

## Related pitfall

Updating a skill/reference/inventory during a normal conversation does not mean the final answer should expose the raw infra-report block. Keep technical audit artifacts out of the user-facing response unless Rodolfo explicitly asks to see them.
