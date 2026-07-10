### Critical: segurador/profile fell

Trigger if:

```text
- segurador token /me fails;
- /debug_token invalid;
- /me/accounts fails;
- all previously known pages disappear from /me/accounts.
```

Alert should include:

```text
Segurador
1Password item name
Error summary
Last OK time
Pages previously known
Immediate action: check profile/token/business/page access
```

### Smart Bidding quarantine for disconnected seguradores — all apps

Rodolfo confirmed that Messenger Page `Status = Review` in Smart Bidding does not send messages and is excluded from the Ciro midnight approval/scheduling flow. This reversible quarantine applies to **all operational apps B001–B011**, not only B011, when a segurador loses its assigned DTR/ChatPion app connection and cannot be recovered before the daily operational cutoff.

Important distinction:

```text
Profile inaccessible but assigned-app link still valid   recovery risk; do not quarantine automatically
Assigned-app link invalid/disconnected                    Drip/Broadcast cannot send; eligible for Review after recovery window
```

Detection adapters differ, but the quarantine contract is global:

```text
B001–B010/B005-2   Meta role drift is an early signal; confirm actual DTR/ChatPion token linkage against the assigned app before SB action.
B011               Validate through the existing DTR/ChatPion token + Meta debug_token route; do not use /roles as connection truth.
```

Any automation must preserve each page's prior status, back up the exact SB rows, key pages by stable IDs, and validate the `Review` readback before reporting protection. On reconnection, restore only after the assigned-app link and affected page connections are validated; restore the saved prior status (normally `Broadcast`) rather than guessing.

### Mandatory incident control plane

A production quarantine automation is incomplete unless its communication and control path is designed with the same rigor as its detector. It must use a dedicated operational incident channel with one thread per active segurador incident, explicit authorized responders, documented reply/action semantics, escalation deadlines, deduplication, and immutable event updates.

Discord is the human control surface, **not** the source of truth. Durable incident state, page snapshots, action attempts, readbacks, overrides, Discord message/thread IDs, and rollback data must live in the runtime incident store and audit log. A human reply such as “recuperado” may trigger immediate validation, but must never restore `Broadcast` without live DTR/Meta/page validation and SB readback. Human replies from unauthorized IDs are informational only and cannot change incident or production state.

### Critical: page fell or lost access

Trigger if a previously known page:

```text
- disappears from /me/accounts;
- is_published becomes false;
- page basic lookup fails;
- subscribed_apps no longer returns expected bot/app;
- conversations endpoint starts failing for an active page.
```

Alert should include:

```text
Segurador
Page name
Page ID
Previous status
Current failing check
Last OK time
SB latest leads/delivery if available
```

### Critical: page temporarily restricted from Messenger sends

Alert de-duplication is mandatory. A page already mentioned as restricted must not be mentioned again while it remains in the same unresolved restricted-page lifecycle. Key suppression by stable page identity (`bot_user + Page ID`, fallback `FB Page ID`), not by campaign/date/Restricted Until. Re-open the alert lifecycle only after DTR/SB proves the restriction was cleared/SENT and the monitor removes that identity from state.

Operational chain for Discord restricted-pages channel: the full DTR sweep is the source of truth; when it finds a new `#2022`, it applies `Restricted Until` in Smart Bidding, validates readback, then posts only that execution's new delta to the restricted-pages channel. Do not post the full baseline or re-announce already restricted pages. For the gestores-facing restricted-pages channel, keep two separate message types: (1) **NOVAS** = pages newly detected in DTR as `#2022` and not yet present as restricted in SB, after automatic `Restricted Until` apply + readback OK; before applying or alerting, the cron must consult the current Smart Bidding row and if `RESTRICTED_UNTIL` is already filled/current for that page, it must ignore/suppress because the action was already done; (2) **RESUMO** = aggregate of current restricted `Broadcast` pages by exit date, not a list of old page names. `On-hold` pages are intentionally paused because they generated under R$100 for the full month of June and are not worth 8 broadcast sends/day, so they are not operationally relevant to gestores in this alert. The `Sites` column belongs in the RESUMO aggregate, listing the domains represented on each date comma-separated. Do not post old pages already in Dash as a visual “baseline” list.

Trigger if DigitalTRChat/ChatPion campaign report shows a subscriber send response like:

```text
(#2022) You're temporarily restricted from messaging users until July 22 at 7:55 AM.
```

Interpretation:

```text
- This is a page/profile Messenger send restriction, not proof that template copy is bad.
- It can contaminate Smart Bidding/Ciro Run Approval and make a whole template look purple if the restricted page is selected first.
- The corrective action is to suppress the page from Smart Bidding routing until after the Meta restriction window.
```

Action rule:

```text
Smart Bidding > Accounts > Messenger > Page > edit page > Page/Broadcast tabs
STATUS = Blocked
RESTRICTED_UNTIL = one calendar day after the DigitalTRChat error date
```

Example: if DigitalTRChat says restricted until July 22, set Smart Bidding `STATUS = Blocked` and `RESTRICTED_UNTIL = 2026-07-23`. After the restriction expires, clear `Restricted Until`, save, and restore `Broadcast` when the page should return to operation. This supersedes the earlier temporary-only `Restricted Until while keeping Broadcast` approach unless Rodolfo explicitly asks for it.

Validated internal DigitalTRChat source: `POST /messenger_bot_enhancers/campaign_sent_status_data` after opening a Campaign report from `/messenger_bot_enhancers/subscriber_broadcast_campaign`. See `smartbidding-dashboard-access/references/digitaltrchat-page-restriction-workflow-2026-07-02.md` for the full endpoint flow and Zytiva test.

### Risk/Critical: page stopped receiving leads

Use SB/ChatPion report. Trigger when an active page with baseline suddenly drops.

Suggested first-pass rules:

```text
IF page is active AND not in maintenance/exclusion
AND LEADS today = 0
AND baseline previous active days > 0
THEN Risk/Critical depending on duration.

IF LEADS_TOTAL stops increasing for N checks/days on a normally active page
THEN Risk.

IF SENDS/BD_SENDS > 0 AND DELIVEREDS/BD_DELIVEREDS = 0
THEN Critical: attempted sends not delivering.

IF Meta page health OK AND SB leads/delivered collapsed
THEN probable ChatPion/SB/template/broadcast issue, not page access.

IF Meta page health broken AND SB leads/delivered collapsed
THEN probable page/profile restriction or access loss.
```

Use a maintenance/exclusion state so planned Utility/template reconfiguration does not alert falsely.

