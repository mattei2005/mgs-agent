### Purple template / approval errors

Rodolfo clarified that purple template status in Ciro/DigitalTRChat should not trigger copy replacement by itself. A shared template can be linked to many pages across multiple seguradores/sites; if the first approval check uses a suspended page, the whole template may show purple even when other pages are healthy. Treat purple as a diagnostic queue and classify by page/segurador cause before deciding action.

```text
Purple cause                                      Operational action
------------------------------------------------  -----------------------------------------
temporary page send restriction until date/time   wait/exclude page; do not rewrite copy yet
developer/profile/segurador fell                 migrate pages/segurador
page permanently restricted/inaccessible          replace/remove page
approval contaminated by first bad page           ask Ciro/system to skip bad page and rerun
unknown                                           inspect DigitalTRChat error report first
```

Avoid one-template-per-segurador as the default; it can explode to hundreds of templates. Prefer intermediate grouping by `site + country/language + vertical + type + risk group` so restricted pages/seguradores are isolated without making the system unmanageable.

### Healthy-page guardrail

Default behavior is **silence on healthy rows**. A row should not trigger Discord if it is normal.

```text
Ativa  Enviando  Leads vs baseline        Discord action
-----  --------  -----------------------  -------------------------------
sim    sim       normal                   silent; only update state/logs
sim    sim       collapsed/stalled        alert RISCO: lead drop
sim    não       below expected/zero      alert RISCO/CRÍTICO
não    qualquer  qualquer                 alert CRÍTICO: page inactive
missing missing   known page disappeared   alert CRÍTICO: lost access
```

This keeps the channel useful: it reports exceptions, not every OK page.

## State File Design

Recommended state path:

```text
/root/mgs-agent/data/segurador-page-health-state.json
```

Suggested structure:

```json
{
  "seguradores": {
    "Dân Kbang": {
      "item": "Segurador Dân Kbang (B005) Token",
      "last_ok_at": "...",
      "token_valid": true,
      "pages": {
        "796622570197092": {
          "page_name": "Patricia Smith",
          "is_published": true,
          "bot_subscribed": true,
          "conversations_ok": true,
          "last_meta_ok_at": "...",
          "last_sb_seen_at": "...",
          "leads_total": 1396,
          "leads_today": 495,
          "bd_sends": 0,
          "bd_delivereds": 0,
          "baseline": {
            "avg_leads_7d": 123,
            "avg_delivered_7d": 4000
          },
          "maintenance_until": null,
          "last_alert_at": null
        }
      }
    }
  }
}
```

## DigitalTRChat purple-template false positives

When Rodolfo reports a template/message bar fully `roxo`, do not treat purple as an automatic copy/template failure. A shared template can be linked to many pages/seguradores/sites; if `Run Approval` starts on a page that is temporarily restricted from messaging, the whole template can look purple even when other pages are healthy.

Operational workflow:

```text
1. Inspect DigitalTRChat broadcast detail for row-level Sent response.
2. If error is (#2022) temporarily restricted until DATE, classify as page/profile restriction.
3. In Smart Bidding > Accounts > Messenger > Page, edit the page.
4. For temporary restriction: Broadcast tab → set Restricted Until = DATE → Save.
5. For permanent/broken page/profile: Page tab → Status = Blocked → Save.
6. Re-run/wait for approval after restricted pages leave the routing pool.
7. If purple remains, then investigate developer/app/profile/template/system.
```

Do not create one template per segurador as the default mitigation; it is operationally too expensive at MGS scale. Prefer shared templates plus `Restricted Until`/`Blocked` page hygiene, with separate templates only for persistent risk groups.

See `references/digitaltrchat-purple-template-diagnosis-2026-07-02.md` for the session-specific evidence and exact UI fields.

## DigitalTRChat Bot Error Audit

When Rodolfo asks to audit bot users/pages for suspension or broadcast failures, use the DigitalTRChat dashboard as the primary source for per-page send errors before touching Smart Bidding state.

Authenticated internal endpoints observed:

```text
GET  /messenger_bot_enhancers/subscriber_broadcast_campaign
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
POST /messenger_bot_enhancers/campaign_sent_status
POST /messenger_bot_enhancers/campaign_sent_status_data
```

Operational sequence:

```text
1. Login per bot user from 1Password.
2. Use the top segurador/account selector; iterate every segurador/account under that user, not only the default one opened after login.
3. Within each segurador/account, enumerate pages/contexts.
4. For each page, use only the latest Completed/sent campaign with a usable report to classify current status; do not classify from older historical Completed reports.
5. Open Campaign report and inspect exact `Sent response`.
6. Cross-check Smart Bidding page status before reporting: ignore current errors for pages already `On-hold` or `Blocked`; `Broadcast` and `Campaign` remain operational.
7. If no latest campaign/report exists, report `NO_REPORT` for that page only as inventory/setup signal.
8. Omit OK pages from Rodolfo-facing output; report only exceptions.
```

Exception policy:

```text
#2022 temporary messaging restriction  If current/latest report and SB status is operational, eligible for SB Blocked + Restricted Until DATE+1 workflow; if mixed with another error, review separately.
#10_WINDOW                             Copy exact error text; inspect the last 5 Completed reports for that page to see whether all five repeat the same error.
#551_UNAVAILABLE                       Copy exact error text; inspect the last 5 Completed reports; usually subscriber-level/unstable, not structural page failure by itself.
#100_TEMPLATE                          Copy exact error text and provide recent page + segurador examples for manual inspection.
PERMISSION / APP_DELETED               Cross-check migration sheet/app-role X state before treating as unexpected; may be planned developer/profile migration.
Any other error                         Report exact bot/user/segurador/page/campaign/error; do not auto-fix.
No report / no pages                    Inventory/setup signal, not critical by itself.
On-hold / Blocked in SB                 Ignore for current broadcast-error reporting because these pages are outside scheduling.
```

The SB-side action and page-count semantics are documented in `smartbidding-dashboard-access/references/digitaltrchat-bot-error-audit-and-sb-restrictions-2026-07-02.md`.

