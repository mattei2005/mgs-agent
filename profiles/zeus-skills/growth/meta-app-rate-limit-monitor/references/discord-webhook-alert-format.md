# Discord Webhook Alert Format — App Rate Limit

## Lesson from B007/Openzed setup

When testing app-rate-limit alerts, `cronjob(deliver=discord:...)` produced a noisy Discord message with wrapper text:

```text
Cronjob Response: <job name>
(job_id: ...)
-------------
...
To stop or manage this job...
```

Rodolfo rejected this because it did not match the clean, human-readable report format shown in the chat.

## Correct delivery pattern

For production app-rate-limit alerts:

1. The scheduled job/script should run silently/local.
2. The script should post directly to the Discord channel webhook.
3. Store the webhook in 1Password as:

```text
Item:  Discord Webhook - app-rate-limit
Field: webhook_url
```

4. Validate the webhook with a GET before relying on it:

```text
GET webhook metadata should return:
channel_id = 1520510823426949313
name       = app-rate-limit
```

5. Send messages via webhook POST JSON payload with `content` and `allowed_mentions`.

## Channel

```text
Channel: #app-rate-limit
ID:      1520510823426949313
```

Operational app-rate-limit alerts must not be sent to `#alerts-infra`. Use `#alerts-infra` only for REPORT-INFRA/inventory changes when creating/modifying skills/scripts/crons/config.

## Human-readable format

Use aligned, compact text blocks. Avoid raw JSON and avoid long prose.

Example:

```text
<@344196393512075265>

Meta App Rate Limit — Webhook Test

Resumo
App   Bloco              Estado  Severidade  Uso App
----  -----------------  ------  ----------  -------------------------------
B007  Openzed isolado    OK      Teste       call 2% | cpu 0% | tempo 3%

Checks
Item                  Resultado
--------------------  --------------------------------
Graph API             Respondendo
Token                 Válido
X-App-Usage           Presente
Canal/Webhook         OK — mensagem limpa sem wrapper de cron

Destino operacional: #app-rate-limit
```

## Implementation notes

- Do not use `cronjob(deliver=...)` for final Discord presentation when a clean operational report is required.
- Use direct webhook POST from the monitoring script.
- Include Rodolfo mention in the content when the alert requires push notification.
- Keep tokens/webhook URLs out of chat and logs; report only item title, field name, URL length, status code, channel ID, and webhook name.
- A successful webhook POST returns HTTP `204`.
