# REPORT-INFRA destination pitfall — never inline in task thread

## Trigger

Rodolfo corrected Zeus after a task final response appended a full `[REPORT-INFRA]` block inside the same Discord thread where the operational task was requested.

## Final rule

`[REPORT-INFRA]` is a dedicated infra-channel report, not a footer in the task thread.

For any infra-affecting task:

1. Execute and validate the task.
2. Update `infra-inventory.json` / audit log as required.
3. Send the formal `[REPORT-INFRA]` only to the proper infra channel/thread using the approved channel route/API/webhook.
4. In the original task thread, reply only with the executive result and validation summary.
5. If the current agent session cannot post to the infra channel, record audit/inventory locally and state the task result without emitting a fake inline `[REPORT-INFRA]` block.

## Wrong pattern

```text
[normal task completion]

[REPORT-INFRA] <@Zeus> <@Rodolfo>
Ação: ...
...
```

This pollutes the operational thread and violates Rodolfo's routing expectation.

## Correct pattern

Original task thread:

```text
Executado. Runner criado, skill atualizada, smoke test passou: Long 723, receita/gasto reconciliados.
```

Infra channel only:

```text
[REPORT-INFRA] <@1496296175014252634> <@344196393512075265>
Ação: criada/modificada
Tipo: script/skill/data
Path: ...
Motivo: ...
Evidência: ...
```

## Checklist

- [ ] Final response in task thread contains no literal `[REPORT-INFRA]`.
- [ ] Formal report was sent via the correct infra route, or audit-only was recorded if no route/API is available.
- [ ] `events-audit.jsonl` records the decision/evidence when report cannot be posted to the correct channel.
