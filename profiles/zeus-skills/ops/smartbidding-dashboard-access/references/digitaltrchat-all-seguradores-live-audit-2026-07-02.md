# DigitalTRChat live audit across all seguradores — 2026-07-02

## User correction captured

Rodolfo corrected Zeus after an incomplete DigitalTRChat audit: logging into a bot user lands on only the first/current segurador/account. A valid audit must iterate the top account/segurador selector and audit every segurador under that bot user.

Do **not** treat the first login context as the full user scope.

## Correct scope for bot/page health audits

For each DigitalTRChat bot credential/user:

1. Login live to `https://digitaltrchat.com`.
2. Open `Subscriber broadcast`.
3. Parse the account/segurador switcher in the top bar:
   - selector entries are rendered as `.account_switch` links;
   - each has `data-id=<fb_rx_account_id>` and visible segurador/account name;
   - the switch endpoint observed is:
     `POST /social_accounts/fb_rx_account_switch` with `id=<data-id>`.
4. For each account/segurador:
   - switch account;
   - reload/open `/messenger_bot_enhancers/subscriber_broadcast_campaign`;
   - parse the `search_page_id` dropdown for pages in that segurador;
   - for each page, query only the newest `Completed` campaign/report for current status.
5. Pages with no newest Completed/report are `sem último Completed/report útil`, not current-error evidence.

## Current-state rule

Current page/app/profile status must come from the latest sent/Completed report per page only. Older Completed reports are historical and can reflect app outages, temporary page restrictions, or profile migrations that later recovered.

Incorrect: aggregate all Completed reports and count any historical error as current.
Correct: for each page context, order Completed campaigns descending by schedule/send time, open the newest Campaign report, classify `Sent response`, and ignore older reports unless Rodolfo explicitly asks for history.

## Last-5 check for recurring policy/subscriber errors

When the newest report contains `#10` or `#551`, Rodolfo wants recurrence context:

- Query the latest 5 `Completed` campaigns for that same page/segurador.
- Open each Campaign report.
- Classify each report by dominant/non-OK categories.
- Report whether the last five are all the same error.

Interpretation from the session:

- `#10_WINDOW` often recurs across the last 5 and may be a structural send-window/policy pattern.
- `#551_UNAVAILABLE` often varies and is usually subscriber-level, not a page/app structural failure.

## Exact error strings observed

`PERMISSION`:

```text
Any of the pages_read_engagement, pages_manage_metadata,
pages_read_user_content, pages_manage_ads, pages_show_list or
pages_messaging permission(s) must be granted before impersonatin
```

`APP_DELETED`:

```text
Error validating application. Application has been deleted.
```

`#10_WINDOW` variants:

```text
(#10) This message is sent outside of allowed window. Learn more about the new policy here: https://developers.facebook.com/docs/messenger-platform/policy-overview
(#10) Essa mensagem foi enviada fora do espaço de tempo permitido. Saiba mais sobre a nova política aqui: https://developers.facebook.com/docs/messenger-platform/policy-overview
(#10) Este mensaje se envía fuera del período permitido. Obtén más información sobre la nueva política aquí: https://developers.facebook.com/docs/messenger-platform/policy-overview
```

`#551_UNAVAILABLE` variants:

```text
(#551) Esta pessoa não está disponível no momento.
(#551) This person isn't available right now.
This person isn't available right now.
(#551) This person isn't available at the moment.
(#551) Esta persona no se encuentra disponible en este momento.
```

`#100_TEMPLATE` variants:

```text
(#100) Nenhum usuário correspondente encontrado
Missing one or more params for template body
User pass unrequired params for template body
(#100) No se puede encontrar la plantilla.
(#100) No matching user found
```

## Reporting rules

- Always state whether all seguradores/accounts were iterated.
- Include number of bot users, login OK/errors, accounts/seguradores visited, page contexts audited, no-report pages, and error pages.
- For `#2022`, split pure vs mixed-with-other-error.
- For `#10` and `#551`, include last-5 consistency summary.
- For `#100`, include at least three page + segurador examples for manual inspection.
- Do not compare `APP_DELETED`/`PERMISSION` to a spreadsheet marker such as column X unless the live/canonical Sheet source is available; do not infer the match from stale local report files.
