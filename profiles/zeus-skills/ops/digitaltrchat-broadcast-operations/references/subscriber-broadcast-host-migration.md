# Subscriber Broadcast host migration

Use this procedure for narrow URL-host migrations in scheduled Messenger Subscriber Broadcast campaigns.

## Operational hierarchy

1. Log into the exact DigitalTRChat user resolved from 1Password.
2. Open `Broadcasting > Subscriber Broadcast` (`/messenger_bot_enhancers/subscriber_broadcast_campaign`).
3. The Facebook account selector at the top represents the current **segurador**. Changing it changes the scheduled broadcast list.
4. Before counting or enumerating campaigns, open the list's `Page` filter and choose the generic `Page` option whenever the control is blank or scoped to a specific Facebook page. This clears the page filter and restores all pages; it is not the `Page` field inside the campaign edit form.
5. For portfolio work, iterate every segurador under each authorized login. Within each segurador, set the status filter to exactly `Pending`, then process every Facebook page represented in the complete filtered result.
6. The campaign table displays 10 rows by default. This is only one table page, not the full eligible set. Traverse pagination pages `1, 2, 3, ...` through the last page or until `Next` is disabled; reconcile the displayed range/total on every transition and deduplicate campaigns by immutable campaign ID. Never stop after the first 10 rows.
7. For a pilot scoped to the “first page”, distinguish the first **Facebook page** from the first **table pagination page**: use the Facebook page name in the first eligible campaign row, then filter/search that exact page and enumerate all of its eligible campaigns.

Do not assume the page dropdown fully represents historical/scheduled rows. Reconcile against the live campaign table and its search results.

## Eligibility and drift gate

- Mutate only campaigns whose live status is exactly `Pending`.
- `Processing`, `Completed`, `Stopped` and `On-hold` are out of scope unless Rodolfo explicitly authorizes them.
- Re-read status immediately before every write. A campaign can move from `Pending` to `Processing` when its configured schedule/timezone is reached.
- If the eligible set changes after the baseline — even by one campaign dropping out — stop before writing and obtain renewed authorization for the reduced set. Never edit a newly processing campaign.
- Record segurador, page, campaign name/ID, schedule, status and exact edit URL in the sanitized baseline.

## Safe row selection

Accept an edit action only when the row is the exact target page/campaign and all predicates pass:

- status text is `Pending`;
- edit href contains `/messenger_bot_enhancers/edit_subscriber_broadcast_campaign/`;
- class contains `btn-outline-warning`;
- the same row exposes a distinct destructive action such as `btn-outline-danger`/`delete`, proving the controls were not confused.

Never click by icon position.

## Exact host migration

Apply host-only mappings, with `finanzas.openzed.com` matched before the parent domain:

- `openzed.com` → `sr.openzed.com`
- `finanzas.openzed.com` → `srf.openzed.com`

Preserve exactly:

- scheme (`http`/`https`);
- path and trailing slash;
- query string and parameter order;
- fragment;
- surrounding copy, emoji and whitespace;
- campaign name, page, labels, targeting, schedule and timezone.

Use URL parsing or an exact-host regex. Never use a broad substring replacement that could turn `finanzas.openzed.com` into an invalid intermediate hostname.

## Message editor handling

Subscriber Broadcast may render the active message through an EmojiOneArea contenteditable while keeping the source in a hidden textarea such as `text_reply_1`.

1. Inspect the active template type and every active URL-bearing field: message text, button Web URL, image destination, generic template, carousel and similar controls.
2. Back up the exact source values and key campaign fields before mutation.
3. Update through the visible editor or its EmojiOneArea API; verify the underlying form control is synchronized before saving.
4. A campaign name containing `[postback]` can still use a Text template with an inline web URL. Inspect live fields rather than inferring from the name.
5. Commit with the visible `Edit campaign` button only after the unsaved value exactly matches the expected host-only delta.
6. Legacy `Non Promo` campaigns can reopen with the correct page but a blank `Message Tag`. In that state, clicking `Edit campaign` shows `Please select a message tag` and performs no save. Do not choose a tag implicitly: adding `ACCOUNT_UPDATE` or another tag changes an unscoped campaign field and requires Rodolfo's explicit authorization.
7. Distinguish the real two-step save chain (`subscriber_bulk_broadcast_edit_action` then `subscriber_bulk_broadcast_add_action`) from unrelated background POSTs such as `home/get_broadcast_summary`; only the save endpoints or the explicit `Campaign updated` success UI prove persistence.
8. A `Completed` campaign's `Campaign report` exposes delivery metrics but not its historical `Message Tag`; the direct edit route can return HTTP 200 with an empty body because only Pending campaigns are editable. Do not infer the old tag from `Non Promo` or delivery success—use an authorized backend database/log source if the exact historical tag is required.

## Verification and rollback

For each save:

1. Require a successful server response or explicit success UI.
2. Reopen the same campaign and read back the exact source value.
3. Compare the whole message/field to the backup-derived expected value; hostname must be the only difference.
4. Compare all non-targeted key fields to the baseline.
5. After the batch, use a fresh browser context/login for independent readback of every changed campaign.
6. On mismatch, restore the exact backed-up value and verify the rollback before continuing.

## Credential-safe DOM inspection

DigitalTRChat account avatars can embed a Facebook access token in an image URL query string. Never print whole account-selector `outerHTML`, image `src`, cookies, storage state or raw network headers. Extract only whitelisted fields such as visible account name, numeric `data-id`, sanitized href path and CSS class; strip query strings from URLs included in diagnostic logs.
