## Runtime Caveats

### DTR page lead scan for Bot pages missing in SB

Rodolfo video correction 2026-07-07: for Sheet tabs where pages exist in Bot/DigitalTRChat but not in Smart Bidding, determine whether the page is worth adding to SB by scanning leads/subscribers inside the Bot user first.

Manual workflow shown:

1. Open the target Bot/DigitalTRChat login from the Sheet user.
2. Go to `Subscriber Manager` (`/subscriber_manager/bot_subscribers`).
3. If the bot user has multiple Facebook accounts/seguradores, use the top account switcher and repeat per relevant account.
4. In the left `Pages` panel, search/select the page by name or PG/page id shown under the page name.
5. After selecting the page, check the counters in the main panel:
   - `Bot subscriber` count;
   - `24h subscriber` count;
   - subscriber table rows (`Subscriber id`, `First Name`, `Last Name`, quick info).
6. Use `Scan inbox` / `Scan` when available/enabled to refresh subscribers for that page, then re-read the counters/table. Important Rodolfo correction: after clicking scan, wait for the scan to finish; it can take time. Expected max wait is about **4 minutes**. Sometimes it keeps spinning and never shows the completion/OK notice. If no OK/completion notice appears after ~4 minutes, refresh the same tab/page, check whether leads/subscribers appeared, and if not, click scan again. Repeat refresh → recheck → rescan until an OK/completion message appears or a real blocker is identified.
7. Classification:
   - if `Bot subscriber > 0` or subscriber rows appear after scan → page has leads/subscribers and may need to be added/corrected in Smart Bidding;
   - if `Bot subscriber = 0`, `24h subscriber = 0`, and table remains empty after scan → likely unused/created but not used; report as no-lead/no-subscriber candidate instead of adding blindly.

Automated version should use the same source of truth: per Bot user + account/segurador + page id, read/trigger subscriber scan endpoint where safe, then classify by subscriber count/table rows. Do not infer lead existence from Smart Bidding because the whole point of this tab is pages missing from SB.

Rodolfo correction 2026-07-07 for missing-in-SB audit Sheets: after scanning, update the Sheet result column immediately. In the `Fase 1 - DTR sem SB` tab, **column D** is the scan result/lead count column: write the numeric subscriber/lead count when found, `0` when scan completes OK with no leads, and `PAGE_NOT_FOUND` when the page is not found under the expected DTR account. Do not finish the audit with only local JSON/CSV reports if the Sheet has a result column to be filled. Detailed reference: `references/dtr-missing-sb-page-lead-scan.md`.

Rodolfo correction 2026-07-07/08: in the same tab, **column E** is authoritative for global exclusion. Rows with `STATUS=BLOCKED` or `STATUS=IGNORAR` must be written to `/root/mgs-agent/data/mgs-global-page-ignore-list.json` and ignored by the entire MGS system: no future Bot/DTR scans, no Smart Bidding registration, no scheduling, no operational backfill, and no future DTR↔SB coverage comparison. Match first by large `FB_PAGE_ID`, then by `bot_user + PAGE_ID/PG`. **Global ignore is a pre-audit gate and wins over all match logic:** even if the page still appears in DTR, gives 100% match, has leads, or can be found in SB, it is an old/off-niche page inherited with the segurador/profile and must not be consulted or reported as pending/actionable. Audit scripts must load the ignore-list before DTR/SB matching and exclude these rows from `DTR sem SB`, `SB sem DTR`, lead scan, restricted-page scan, template/page health checks, and registration payloads. The current canonical JSON stores records under the top-level key `entries`; treating only `pages` or the root object as the record list silently disables the denylist. Fail closed when `entries` is absent or not a list, reconcile the exact `FB_PAGE_ID` intersection before freezing a batch, and record every ignored Page in the exclusion partition. Column F then describes the action only for non-ignored rows; if it says `cadastrar na dash e colocar o status broadcast e escolher o template`, the matching registration sheet (`gid=907050576`) is the execution payload for creating SB Messenger Page rows.

#### Conectar Page e habilitar Subscriber Manager auto scan

When Rodolfo explicitly authorizes reconnecting Pages and enabling Subscriber Manager auto scan for the disconnected subset:

1. Freeze the eligible Page set after applying the global-ignore gate, then correct existing SB rows first by the exact large ID; update the coupled pair `PAGE_ID + UTM_CAMPAIGN` and validate preserved fields.
2. Connect each Page through the same DTR action as the blue plug: `POST /social_accounts/enable_disable_webhook` with `page_id`, `enable_disable=enable`, and `restart=0`. Success requires a fresh Page-card readback showing class `disable_webhook`; HTTP 200 or the success message alone is insufficient.
3. Start auto-scan writes only after every eligible Page is connected. In the exact imported-account context, read `/subscriber_manager/get_page_details`; `Enable auto scan` with `enable_disable=1` means the background action is available. The UI-equivalent trigger is `POST /subscriber_manager/enable_disable_auto_sync` with `page_id` and `operation=1`. Record the exact Page/account and require HTTP acceptance or the UI background-processing notice; an empty HTTP 200 body is compatible with this route.
4. **Rodolfo correction:** `Enable auto scan` is a background-job trigger, not a durable on/off setting. After the job is accepted, the button normally becomes clickable as `Enable auto scan` again; that does not mean the scan was undone or failed. Never require `Disable auto scan` to persist across a later session, never label the button's return as `AUTO_SCAN_PERSISTENCE_UNSTABLE`, and never enqueue duplicate jobs solely because the button is clickable again. Retry only after an explicit transport/application error or separate evidence that the background job was not accepted/executed.
5. Roll back any Page accidentally touched despite the global-ignore gate: do not enqueue another auto-scan job, disable the bot connection when the Page was originally disconnected, and prove the original connection state in a fresh session. Do not create a missing SB row unless that separate registration scope is explicitly authorized.

