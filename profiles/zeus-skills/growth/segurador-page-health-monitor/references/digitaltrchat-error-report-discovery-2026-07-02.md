# DigitalTRChat / ChatPion error report discovery — 2026-07-02

## Context

Rodolfo surfaced the `Last 7 days error report` modal inside `digitaltrchat.com` / ChatPion. The modal showed a page/message sending restriction like:

```text
(#2022) Você está com uma restrição temporária de enviar mensagens a usuários até 22 de julho às 04:32.
```

This matters because template approval colors can become misleading: if Ciro's approval process chooses a suspended page first, the whole template can appear purple even when other pages/seguradores behind the same template are healthy.

## Documentation checked

Public docs reviewed:

```text
https://demo.chatpion.com/documentation/api-channels.html
https://demo.chatpion.com/documentation/
https://xeroneit.net/knowledgebase/api/
https://digitaltrchat.com/api/doc
```

The public API documentation exposes basic user/contact/label/flow/subscriber endpoints. The closest documented fields found were on `subscriber_information`:

```text
unavailable
last_error_message
```

No public documented endpoint was found for:

```text
Last 7 days error report
page suspension status by page
broadcast/template approval error aggregation
temporary page message restriction with unlock timestamp
```

## Operational conclusion

Do not rely on the public API docs to solve purple-template diagnosis. Treat the dashboard modal as likely powered by an internal authenticated endpoint.

Preferred investigation sequence:

1. Log into `digitaltrchat.com`.
2. Open the `Last 7 days error report` modal.
3. Use browser DevTools/Network to capture the endpoint called by the modal.
4. Check whether the endpoint works with the logged-in session cookie/API key.
5. If stable, build an internal collector to extract: bot/user, page, error text, error time, and restriction-until timestamp.
6. If no stable endpoint exists, use logged-in browser automation as fallback to scrape the modal.

## Decision rule for purple templates

Purple is not a copy/template-change decision by itself. Purple is a diagnostic queue.

Classify purple rows by cause:

```text
Cause observed                                      Action
--------------------------------------------------  -----------------------------------------
Temporary restriction until date/time               wait/exclude page; do not rewrite copy yet
Developer/profile/segurador fell                   migrate pages/segurador
Page permanently restricted/inaccessible            replace/remove page
Approval contaminated by first suspended page        ask Ciro/system to skip bad page and rerun
Unknown purple                                      inspect DigitalTRChat error report first
```

## Template grouping recommendation

Do not create one template per segurador by default; 220+ templates is operationally too heavy.

Use intermediate grouping instead:

```text
site + country/language + vertical + type + risk group
```

Example:

```text
Openzed US-CC-EN/EN AV g001-d — healthy group
Openzed US-CC-EN/EN AV g001-d — restricted/recovery group
Openzed US-CC-EN/EN AV g001-d — canary/test group
```

The goal is to isolate bad/suspended pages enough that they stop contaminating shared approval results, without exploding template count.
