# Meta App Roles — manager channel boundary

## Trigger

Use when maintaining `meta-app-roles-watch` or any alert that posts into the app-specific Discord channels `B001`–`B010` / `B005-2`.

## Durable lesson

The app-specific channels are **manager-facing operational alert channels**, not Zeus internal status channels.

Post there only when the content is directly actionable for the app/channel owner, such as:

- app role user added/removed;
- segurador/profile absent from the app;
- token/API/rate-limit/auth problem that affects that app;
- manager-facing app health alert.

Do **not** post there:

- Zeus internal correction notes;
- broad “monitor fixed” explanations;
- reconciliation implementation details;
- generic infra/status reports;
- anything whose natural destination is Zeus / `#alerts-infra`.

## Validation before fan-out

Before sending a message to all B001–B010 channels, classify:

```text
Question                                      If yes
-------------------------------------------- -----------------------------
Does a manager need to act on this app?       Post to that app channel
Is this only explaining a Zeus/script fix?    Keep in Zeus/#alerts-infra
Is this broad infra status?                   Keep in #alerts-infra
Would the message confuse a gestor?           Do not send to app channels
```

If a wrong internal/status message is posted to the app channels, delete it and record the correction. Validated deletion returns Discord HTTP `204` per message.

## Incident note

On 2026-07-02 Zeus sent a broad internal correction/status message to all B001–B010 app channels after fixing sheet reconciliation. Rodolfo correctly flagged: “isso não deveria estar aí”. Zeus deleted the message from the 10 channels and recorded this boundary.
