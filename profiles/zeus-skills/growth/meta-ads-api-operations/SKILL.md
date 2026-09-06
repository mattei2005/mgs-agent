---
name: meta-ads-api-operations
description: "Operate and troubleshoot MGS Meta Ads API workflows for Ares: read/dry-run/write phases, proxy/IP isolation tests, 1Password-backed tokens/proxies, safe campaign/adset/adcreative/ad creation, cleanup of partial objects, and interpretation of Meta endpoint-specific failures."
tags: [meta-ads, ares, growth, marketing-api, proxy, webshare, adspower, 1password, campaigns, ads, troubleshooting]
---

# Meta Ads API Operations — Ares/MGS

## When to use

Use this skill when working on Meta Ads / Facebook Marketing API operations for MGS, especially when:

- Ares needs to read Meta campaign/adset/ad/creative data.
- Ares is testing replacement campaign creation, clone-source, or intraday rule execution.
- Rodolfo suspects VPS/datacenter IP reputation, proxy, AdsPower, Webshare, token, or app trust issues.
- Meta returns endpoint-specific errors such as `code=31`, `subcode=3858385`, `Autentica tu cuenta`, `code=100`, or `messenger_doc` validation problems.
- You need to compare direct VPS vs residential/proxy behavior without exposing credentials.

## Safety model

1. **Read-only and dry-run first.** Always verify token/account/campaign visibility before write.
2. **Never print credentials.** 1Password tokens/proxies may be used internally only; report field names and lengths at most.
3. **Write tests must be controlled.** Campaigns/adsets/ads should be created `PAUSED`, with budget guardrails and a known loser/source campaign.
4. **Cleanup partials immediately.** If any write step fails after creating a campaign/adset/adcreative, mark partial campaign `DELETED` and verify via GET before reporting.
5. **Interpret failures by endpoint.** If campaign/adset/adcreative creation succeeds but `POST /ads` fails, do not call it a general account/IP failure.
6. **Preflight credential cutovers before confirmation.** Inventory exact 1Password item IDs/titles, compare paired token fields in-process without printing values or hashes, then prove app/user/account/scopes and the live Marketing API tier. Do not change active references until the critical credential confirmation is received.
7. **Diff authorization against the executable selection before every irreversible stage.** Materialize the last explicitly approved campaign count, asset count, partition/mix, IDs, budgets and statuses, then compare them programmatically with the concrete runtime selection before reservation/release, Meta media pre-stage, upload and campaign write. “Execute tudo” authorizes only the immediately preceding enumerated scope; an engine requirement or newly discovered stock need never widens it. On any mismatch—even a small increase or reduction—persist the current state, block new writes, report the exact delta and wait for Rodolfo. Do not roll back, release or delete already-mutated objects without the authorization required for that separate action.
8. **Treat repair and replacement as different scopes.** If Rodolfo changes an in-flight instruction from missing-only recovery to “delete and recreate,” stop repairing the old objects immediately. Read back the named targets, perform only the authorized terminal transition, verify it, close/supersede the old checkpoint and use a new request/idempotency identity for the replacement. Never add a missing ad to an old campaign after the user explicitly ordered replacement, and never claim `DELETED` when the live result is `ARCHIVED`, `PAUSED`, blocked, or ambiguous.

### Live execution audit after Marketing API Full/Standard activation

When Rodolfo asks whether `standard_access` made campaign creation faster, audit the complete route rather than trusting the final summary or Discord wall time:

1. Confirm the exact app, user/token route and ad account with a fresh read-only request whose live usage header says `ads_api_access_tier=standard_access`. A stale operation label such as `active_guarded_development_access` is bookkeeping drift, not tier proof.
2. Freeze the approved execution contract: campaign numbers/count, mode, vehicle or other partitions, READY/TESTED mix, exact asset set, budget, status and schedule. Compare it with reservation audit, inventory readback, media registry, sealed manifest and engine checkpoint before allowing the next stage.
3. Reconstruct timestamps separately for analysis, human decision wait, cleanup, Drive moves, selection/reconciliation, local derivative rendering, Meta media pre-stage, manifest build/prevalidation, engine writes, recovery/readback and post-processing. Report each phase distinctly.
4. Compare the engine/API segment—not the entire conversation—to the prior development-tier baseline. Standard access should remove only the fixed development cooldown; it does not make research, custom scripting, Drive work, video rendering or post-processing faster.
5. Treat live `Searching`, broad file reads, helper-script authoring or patching after execution approval as route overhead and automation debt when the operation should already be covered by the deterministic campaign engine. Measure that overhead separately from Meta latency and identify which input/contract is missing from the canonical runner.
6. Verify the external outcome independently: campaign/adset/ad cardinality, IDs, lineage/source IDs, budget, status/start time, Page/UTM, video readiness/association, Drive parents/statuses, inventory history, budget envelope and all recovery effects. A successful command or agent narrative is not completion.
7. If monitoring another active agent reveals scope drift, send one precise fail-closed gate to the active execution: stop only future writes, preserve current state/IDs, avoid automatic rollback, identify the approved versus selected delta and require Rodolfo’s explicit decision. Validate both message readback and acknowledgement by the target agent.

For the development-tier baseline and phase accounting, see `references/meta-campaign-throughput-diagnosis-cpv-2026-08-28.md`.

Do not infer engine behavior from a shared/global tier cache alone. Compare it with the active bundle checkpoint's `quota.ads_api_access_tier`, effective ceiling and wait records. If the global request says `standard_access` but the bundle begins with tier `null` and the unknown-tier 100/120 limits, report a tier-propagation/observability gap; do not credit Standard for removed cooldowns until the lane itself proves it. Preserve error chronology as well: an initial transient child `code=2` and a later reconciled `3858385` authentication blocker are separate stages, not competing summaries.

Session-specific partial evidence, phase timings and final acceptance gates: `references/meta-standard-access-live-run-audit-2026-09-05.md`.

### Meta app/token cutover preflight

For a requested production token replacement:

1. Inventory exact current and candidate 1Password items. Similar titles or date-prefixed duplicates are distinct candidates; never choose by partial title alone.
2. Fetch each item once with `op item get --format json --reveal`, select the first **non-empty** approved secret field (`credential`, then `token`), and keep values only in process memory.
3. When both a generic token item and an account-specific item were supplied, verify their secrets are equal internally. Report only item names, lengths and equality; never print the value or a secret-derived hash.
4. Probe the candidate read-only with `/debug_token`, `/me`, paginated `/me/permissions`, the exact `act_{account_id}` identity, and a one-row campaign GET. Validate expected `app_id`, user identity, account name/status/currency/timezone and every required scope.
5. Parse `X-Ad-Account-Usage` and `X-Business-Use-Case-Usage` independently. Advanced Access on every scope does **not** prove Marketing API Full Access; only a live `ads_api_access_tier=standard_access` does. If the candidate still returns `development_access`, say before confirmation that the cutover will not remove the development cooldown.
6. Present the critical confirmation with exact account scope, current app/user/tier, candidate app/user/tier, rollback preservation and validation plan. Do not widen the swap to another account merely because it shares the old token or app key.
7. After confirmation, use an app-specific key/cache path, retain the old reference/cache for rollback, update every active consumer, run a read-only/dry-run smoke and read back the credential item actually resolved. Deleting/revoking the prior token is a separate critical operation.

### Multi-account cutovers, Page parity and token retirement

- **App role is not token identity.** Adding Rafael/another profile as app admin does not switch Ares, mutate an existing token or prove which user a 1Password field represents. After any mid-session 1Password edit, re-read the exact item and use `/debug_token` + `/me`; never infer identity from the title, prior read or the user's role assignment.
- **Revalidate each account independently.** A token that passes one ad account cannot be propagated to another just because the app and scopes match. For every target, check exact account name/status/currency/timezone, one campaign read, expected pixel/dataset and every Page/identity dependency.
- **Page-backed operations require Page parity, not account visibility.** Before replacing a Messenger/Eggbev-style token, paginate `/me/accounts?fields=id,name,tasks` for both old and candidate tokens. Require the candidate to cover every Page the old route may use with `ADVERTISE` (and any additional required tasks). Account HTTP 200, pixel visibility and complete OAuth scopes are insufficient if Page sets differ.
- **Prefer catalog comparison before an all-ads crawl.** Comparing the paginated old-token and candidate-token Page inventories is faster and more decisive for credential eligibility. Scan ads only when the canonical Page set cannot be derived from the old token, operation registry or current request.
- **Fail closed per account.** If one account passes and another lacks Page coverage, do not perform the original all-account cutover. Report the exact per-account result; a reduced cutover needs fresh authorization because its scope changed.
- **Retire credentials only after a consumer sweep.** Inventory active config, account registries, operation sources, cron/runtime scripts, monitor allowlists, cache paths and executable rollback/recovery scripts. Historical audits/backups may retain item names as evidence, but no executable path may depend on the item being removed.
- **Exercise every legacy consumer after a cutover.** Engine/auth smokes do not prove reports and guardrails migrated: live profile scripts may still hardcode an old `META_ITEM` or inherit the generic token cache. Resolve the item from the account registry, force an account-specific cache path before importing the shared Meta helper, then validate the next real scheduler tick for each report/guardrail lane and require its failure streak to return to zero.
- **Name every deletion target.** “Delete the old token” is ambiguous when accounts use different users/items. State each exact 1Password item and which account it serves. `op item delete` moves an item to Recently Deleted for 30 days; `--archive` is different. Deletion remains a separate critical confirmation even after the credential swap is approved.

Session-specific proof and safe branching: `references/multi-account-token-cutover-page-parity-2026-09-02.md`.

Detailed permission/tier and cutover verification: `references/meta-app-full-access-permissions-2026-08-21.md`.

## Standard diagnostic flow

### Fast status check for Ares OpenzedFinanzas-CC-ES

When Rodolfo asks whether Ares is already analyzing/running Spain credit-card campaigns in Spanish, answer from runtime/config rather than memory:

1. Check `ares-gateway.service` is active.
2. Inspect `/root/.hermes/profiles/ares/cron/jobs.json` for these jobs:
   - `Ares Meta intraday R1-R5 dry-run` (`aa9e01a5ec4a`) — every 30m, read-only/dry-run.
   - `Ares Meta reativar-todas dry-run` (`c6c737070d3f`) — daily aligned to 00:30 Europe/Madrid, read-only/dry-run.
   - `Ares Meta HOA manager report - Openzed ES` (`e84a8db81fb3` or documented successor) — manager checkpoints, read-only/dry-run.
3. Inspect `/root/mgs-agent/data/ares/meta-ads/operations/OpenzedFinanzas-CC-ES.json` and `/root/mgs-agent/data/ares/meta-ads/accounts/1356770869843984.json` for scope.
4. Report the operational truth concisely: account `act_1356770869843984`, observed name `OpenzedFinanzas-ES-CC-ES-03`, country `ES`, vertical `CC`, timezone `Europe/Madrid`, current mode `read-only/dry-run`, and whether write is enabled.
5. Do not say Ares is executing campaign changes unless config says `write_enabled=true` and a validated write log exists.

### Phase 1 — Credential/proxy intake

For Webshare/AdsPower proxy items in 1Password, the known-good field mapping is:

```text
1Password field  Meaning
---------------  ---------------------------------------
Username         proxy username
Credential       proxy password
Host             proxy host/address
Port             proxy port
Protocol         usually `http` for Webshare tests
```

Use `Protocol=http` first unless Webshare explicitly shows SOCKS5. Even when calling `https://graph.facebook.com`, the proxy URL is commonly `http://user:pass@host:port`; the HTTP proxy performs CONNECT tunneling.

### Phase 2 — Validate egress IP before touching Meta

Compare direct VPS egress with proxied egress:

```bash
curl -fsS https://api.ipify.org
HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" curl -fsS https://api.ipify.org
```

Expected MGS pattern observed:

```text
Direct VPS       Hetzner / Ashburn / datacenter
Webshare proxy   Comcast or other residential/ISP-looking IP
```

If the proxied IP does not change, stop before Meta testing.

### Phase 3 — Meta dry-run through proxy

Run the relevant Ares script with proxy environment variables and `--dry-run` first. Python `urllib.request` honors `HTTPS_PROXY` / `HTTP_PROXY`, so a code change is not required for initial proxy isolation if the script uses urllib.

Example shape:

```bash
HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" \
python3 /root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py \
  --loser-campaign-id <campaign_id> \
  --daily-budget-usd 25 \
  --creative-count 3 \
  --creative-mode video_data_minimal \
  --dry-run
```

### Phase 4 — Controlled write, only after explicit approval

Write tests may create real Meta objects, even if paused. Get explicit confirmation before running without `--dry-run`.

Use the corrected video/image asset flow for Messenger clone-source tests:

```bash
HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" \
python3 /root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py \
  --loser-campaign-id <campaign_id> \
  --daily-budget-usd 25 \
  --creative-count 3 \
  --creative-mode video_data_minimal
```

## Interpretation rules

### Marketing API Full access: interpret Dashboard screenshots precisely

When Rodolfo asks whether an app can already apply for the higher Marketing API tier, separate **eligibility**, **submission**, **approval**, and **live activation**:

1. Use the current labels **Marketing API Access Tier: Limited access / Full access**. Older pages may still say Ads Management Standard Access or show superseded thresholds.
2. Treat a green combined requirement such as **“at least 500 Marketing API calls with error rate below 15%”** as proof that this eligibility gate is satisfied. Do not derive the error rate from a large activity count alone.
3. A green Business Verification gate plus a green call/error gate means the app is eligible to request Full access. A gray **App Review** gate means review is still pending/not approved; it does not negate eligibility to submit.
4. Answer “yes, eligible to apply” separately from “approved.” The app remains Limited/development tier until Meta approves the review and the live header reads `ads_api_access_tier=standard_access`.
5. The normal submission route is `App Review > Permissions and Features > Marketing API Access Tier > +Upgrade`. If a screenshot cuts the Action column (for example, only `No A…` is visible), never reconstruct the hidden label or claim the button is present. State that eligibility is proven, but request a full-width/live view only if the action control itself must be diagnosed.
6. Prefer the live App Dashboard requirement indicators and Meta’s current Marketing API Rate Limiting documentation over stale cached authorization text during a nomenclature/threshold transition.
7. Before advising any checkbox or text field, identify the exact form surface: **Requests**, **Renewal**, **Allowed usage**, **Data handling**, or platform-specific **Reviewer instructions**. A checkbox in Renewal certifies existing approved access; it does not request a new upgrade.
8. Keep guidance field-scoped and minimal. Preserve accurate pre-filled website instructions that already passed review; do not replace them with server-side operations the reviewer cannot click. If extra Marketing API context is useful, append it as clearly labeled context, not as a website test step.
9. For controller/processor questions, explain the decision criterion without exposing agents, credentials, vault items, or topology. Prefill proves only the prior submitted answer, and the controller country follows the responsible legal entity—not the human reviewer.
10. After submission, report **Review in progress**, not approval. Do not call the tier active while the live quota header remains `ads_api_access_tier=development_access`.
11. On the post-review page, a top-level **Not submitted** plus “Nothing has been added to this submission yet” can describe a new empty draft after Meta finished the prior request. Read **Previous submissions** before classifying the review as failed or withdrawn.
12. **No items in API Access Tier** on that summary page is not, by itself, proof that the tier upgrade was omitted or rejected. Verify the token’s exact `app_id`, then make a real read-only ad-account request and parse both quota-header families. `ads_api_access_tier=standard_access` proves the Full tier is operationally active; a missing Dashboard screenshot is then a visual-evidence gap, not a runtime blocker. If the header still says `development_access`, do not claim activation.
13. After activation, hand off testing to the owning acquisition agent with the exact app ID and sanitized proof. Require independent app/token/tier verification and read-only/dry-run consumer smokes; a `PAUSED` write canary still needs an already authorized exact operation scope.

Detailed requirements and post-approval verification: `references/meta-app-full-access-permissions-2026-08-21.md`.

For the complete reusable submission flow—including Allowed usage text, Requests versus Renewal, Data handling/controller/processor rules, Reviewer instructions, pre-submit checks, and live post-approval proof—load `references/meta-marketing-api-full-access-app-review.md`.

### Rodolfo scope: no System User unless explicitly reopened

Rodolfo explicitly removed Meta System User from scope for Ares/MGS. Do not present System User as a requirement or default recommendation in Meta/Ares guidance unless he explicitly reopens that path. Use the valid user/admin token path within the permissions/assets available to that user.

### Replacement campaigns: clone first, do not build from zero

For MGS replacement campaigns, the correct primary route is **native Meta clone/copy**, not manual campaign/adset/ad creation from zero. Creating from zero can hit page permission, account authentication, or `POST /ads` checkpoints and does not prove the clone route is blocked.

Operational sequence:

1. Choose a known source campaign/adset/ad that is already working.
2. Prefer native copy endpoints (`/{campaign_id}/copies`, `/{adset_id}/copies`, `/{ad_id}/copies`) and keep copied objects `PAUSED`.
3. If copy fails with `code=100` / `error_subcode=3858504` / `El anuncio no debe incluir mejoras estándar`, treat it as a source-ad `standard_enhancements` legacy-field problem.
4. Next test should use another newer/cleaner source ad without legacy standard enhancements, or test the exact copy parameter that suppresses/normalizes standard enhancements into individual creative feature controls.
5. Do not keep creating/deleting fresh campaigns from scratch unless the test is explicitly diagnostic and approved.

Reference: `references/meta-native-clone-standard-enhancements-2026-06-18.md`.

### Campaign clone rate limits: development tier is not production capacity

When a clone/create workflow returns `code=17` / `error_subcode=2446079`, inspect the live tier and both quota-header families before retrying. A valid token with `ads_management` can still be on `development_access`; Meta documents that tier as a 60-point ad-account score ceiling, while writes generally cost 3 points. Project the complete plan—including `validate_only` mutation calls and final-readback reserve—before the first write.

Operational rules:

1. Parse `X-Ad-Account-Usage` independently from `X-Business-Use-Case-Usage`; a low BUC percentage does not prove ad-account score capacity.
2. Upgrade the MGS-controlled app to Marketing API Full Access for production capacity and validate `ads_api_access_tier=standard_access` by live header. This does not require a System User.
3. For faithful deep copy above the synchronous child limit, use native `/{campaign_id}/copies` through `/{ad_account_id}/async_batch_requests`, keep the copy `PAUSED`, poll with bounded backoff, and read back the source-to-copy ID map.
4. Do not treat Graph batch as a quota bypass: every child operation still counts.
5. On `17/2446079`, preserve valid PAUSED objects and defer readback until the header reset; do not clean them up solely because the final GET was throttled.
6. While the live tier remains `development_access`, use one campaign per five-minute window, pre-upload/cache media IDs, and move heavy historical reconciliation outside the mutation window.

Full causal proof, current Meta limits, MGS reconstructed score, implementation order, and verification checklist: `references/meta-clone-development-tier-rate-limit-2026-08-20.md`.

For bulk/high-scale work, do not optimize only the quota wrapper. Separate pure clone from new-media replacement, eliminate live `Searching`/patching, pre-stage media IDs, use independent account lanes, batch dependencies and native future scheduling. Current CPV code/file findings, benchmark math, target architecture and rollout gates: `references/meta-campaign-engine-high-scale-architecture-2026-08-21.md`.

For Meta App Review and maximum useful Ares access, distinguish per-permission Advanced Access, Marketing API Access Tier Full Access, and actual Business/Page/IG/pixel assignments. Exact core, MGS creative/Messenger, optional modules, security and readback checklist: `references/meta-app-full-access-permissions-2026-08-21.md`.

### Proxy/IP isolation

If the same payload/token fails direct from Hetzner and also fails through Webshare/AdsPower residential proxy, do **not** conclude “it is just Hetzner.” The likely problem is app/token/API trust or the specific Marketing API endpoint.

If it passes through proxy and fails direct from VPS, then IP/reputation is strongly implicated.

### `POST /ads` can be separately blocked

Observed durable pattern:

```text
Campaign API       OK
Adset API          OK
Adcreative API     OK, including video_id flow
POST /ads          blocked: code=31 / subcode=3858385 / Autentica tu cuenta
```

This means the account/token can perform some write actions, but Meta blocks ad creation/modification specifically. Report the endpoint boundary clearly.

Additional readback rules for `3858385` and native Ad Copies:

1. `ACTIVE`/`LEARNING` at campaign or ad-set level is not proof of a complete `1×1×3`. Paginate the live ads edge and validate every expected slot independently.
2. The Ads Manager acknowledgement **“Confio nesse anúncio e ele está correto”** is a human UI gate; do not invent an undocumented Marketing API parameter for it. Treat the checkbox plus **Publicar** as operator evidence only, then prove clearance with a fresh API write/readback.
3. Do not assume one UI acknowledgement clears the account globally. A fresh ad or fully recreated campaign may still receive `3858385`; classify deletion/recreation as a diagnostic canary, not a cure.
4. A native `/{ad_id}/copies` child can return HTTP success without `copied_ad_id` and still materialize the ad. Before retrying, perform bounded live GET reconciliation in the target ad set by expected slot/name, asset or creative identity, and `source_ad_id`. If the ad exists—even `PAUSED/WITH_ISSUES`—persist its ID and never replay that slot.
5. `DELETE`/archive and even status edits may themselves be blocked by the same pending action. Report the exact live status and preserve the partial state; do not rewrite a failed terminal transition as completed.

Observed evidence and the incomplete Standard-access benchmark are in `references/meta-standard-access-live-run-audit-2026-09-05.md`.

### Advanced Access app/token is not sufficient proof

If Rodolfo swaps to a Meta app/token with Advanced Access and the failure still appears only at `POST /ads`, do **not** keep treating ordinary app permissions as the primary hypothesis. A 2026-06-18 retest with a new Advanced Access app/token reproduced the same boundary: dry-run OK, campaign/adset/adcreative OK, `POST /ads` failed with `code=31 / subcode=3858385`, and cleanup verified the partial campaign as `DELETED`.

Interpretation: Advanced Access can be necessary, but it is not sufficient to clear this checkpoint. The next decisive isolation test is same script/token/payload from a different host/IP/datacenter, preferably Hostinger when comparing against Bruno Okamoto/student success patterns.

### `messenger_doc` is not valid input for rebuilt creatives

For Messenger campaigns, do not blindly resend `object_story_spec` / `asset_feed_spec` as returned by Meta if it contains `https://fb.com/messenger_doc/`. Meta may expose it in existing creatives but reject it as an external destination when creating a new adcreative.

Prefer clone-source based on clean assets:

```text
video_id      for existing video creatives
image_hash    for existing image creatives
```

Use `ares-meta-replacement-clone-videoid.py` / `video_data_minimal` when available.

### Rodolfo scope correction: no System User

Rodolfo explicitly does **not** want Meta System User in the Ares/MGS operating path. Do not present System User as a requirement or next step unless he reopens that path. Work within user/app-token + app permissions + BM/Page/ad account asset access.

For OpenzedFinanzas clone/replacement, the relevant token/app permission bundle is:

```text
read_insights
pages_show_list
ads_management
ads_read
business_management
instagram_basic
pages_read_engagement
pages_read_user_content
pages_manage_engagement
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

### Clone vs create-from-zero: do not conflate routes

When Rodolfo asks to clone Meta campaigns, do **not** implement it as “create a new campaign from generic Ares defaults” and call that a clone. There are two separate modes:

```text
Mode                         Meaning
---------------------------- ------------------------------------------------
Replacement Ares padrão      1 campaign / 1 adset / 3 ads / USD 25 / PAUSED
Clone fiel                   Copy the source campaign/adsets/ads structure and writable fields
```

For clone fiel, first build a source mirror via GET:

```text
1. GET source campaign
2. GET all source adsets
3. GET all source ads/creatives
4. Classify fields as writable vs read-only/derived
5. Create/copy PAUSED objects step-by-step
6. Validate source vs clone with GET after each step
```

Do not accept a structurally working clone as “perfect” if critical writable fields differ. A 2026-06-19 Elena Santana test proved campaign/adset/ad creation and activation can work, but the clone was not perfect because attribution changed from `7-day click + 1-day view` to `1-day click`.

### Attribution 7/1 clone diagnostic before declaring “inevitable”

If a source adset shows `7-day click + 1-day view` but the clone comes back as `1-day click`, do not immediately call it a Meta limitation. First rule out our own payload bug:

```text
1. GET source adset with attribution_spec, attribution_setting, use_unified_attribution_setting.
2. GET clone adset with the same fields.
3. Check scripts for hardcoded 1-day click attribution_spec.
4. Test one PAUSED adset using attribution_setting=7d_click_1d_view, not attribution_spec.
5. If needed, test use_unified_attribution_setting=true + attribution_setting=7d_click_1d_view.
6. Only after those fail, investigate native/async copy or UI automation.
```

Native/async copy is the preferred path for a true Meta clone because it may preserve internal metadata not exposed in manual create payloads. But it is not proof that rebuild is impossible until `attribution_setting=7d_click_1d_view` has been tested directly. If native/async copy preserves 7/1, promote it to the official clone-fiel route. If public API/tier blocks native copy while Ads Manager UI duplicates normally, the fallback is AdsPower/UI automation rather than accepting a non-identical clone.

See `references/openzedfinanzas-clone-attribution-native-copy-2026-06-19.md` for the session-specific details and message template used to align Ares.

## Ares Meta cron failures / `#logs-aquisicao` spam

When Meta cron jobs in Ares repeatedly timeout or spam `#logs-aquisicao`, first inspect `/root/.hermes/profiles/ares/cron/jobs.json` and the no-agent script path. For job `aa9e01a5ec4a` (`Ares Meta intraday R1-R5 dry-run`), repeated 120s timeouts can be caused by an invalid/deleted Meta app token, not by Hostinger. The observed durable signature is Graph API `HTTP 400`, `OAuthException code 190`, message `Error validating application. Application has been deleted.` In that case, pause the affected Meta cron jobs (`aa9e01a5ec4a`, `c6c737070d3f`, `0598c0dc469f`) to stop Discord spam, set a clear `paused_reason`, and wait for the `Token Meta API` 1Password credential to be replaced. Details: `references/meta-cron-invalid-app-token-timeout-2026-06-18.md`.

### 1Password throttling in recurring Meta crons

If the intraday wrapper emits `runner_exit_1` repeatedly and the runner fails before writing a new audit, test the credential lookup separately. The durable signature is `Too many requests` / `rate-limited` from the 1Password CLI while `op whoami` may still look healthy.

Operational rules:

1. Pause the affected Ares cron immediately to stop repeated Discord alerts and additional 1Password requests.
2. The shared Meta helper is **cache-first**: use the fresh protected cache before contacting 1Password. The default refresh interval is 24 hours; do not regress to one `op item get` on every cron run.
3. Refresh with exactly one `op item get --format json --reveal`. Never probe candidate field labels separately.
4. Serialize refreshes with a cross-process lock and double-check the cache after acquiring it. This prevents simultaneous cron processes from creating a credential-read stampede.
5. Persist the token only in `/root/.cache/mgs/ares-meta-token.json`, with parent mode `0700`, cache and lock mode `0600`, and atomic replacement. The path stays outside Git.
6. A transient 1Password failure may use the bounded stale cache for at most 7 days. An explicit/forced refresh fails closed and must not fall back to a rejected token.
7. Validate concurrency synthetically: several simultaneous processes must produce one refresh, preserve permissions, and expose no token. Then run two real read-only Meta auth checks and confirm `cached_at` does not change, followed by an intraday dry-run with `exit 0`, `errors=[]`, and `write_enabled=false`.
8. Resume a paused cron only after those checks pass. If no valid cache exists, keep it paused until one successful 1Password lookup seeds the cache.

Implementation: `/root/mgs-agent/scripts/ares-meta-common.py`.

Detailed incident signature, reproduction boundary, cache contract, and resume checklist: `references/ares-intraday-1password-rate-limit-2026-07-10.md`.

## Meta Business browser writes with a logged Facebook user

When Rodolfo asks to create ad accounts or change Business Settings using a Facebook user already logged into the persistent browser profile, preserve that exact identity and use manual passkey/2FA through localhost-only noVNC. Confirm the Business target and current assets before write, read disabled controls/tooltips, and validate each new Ad Account ID plus `Owned by` after creation. Do not silently substitute a different API user/token.

Treat Meta reauthentication as an explicit auth gate during preflight. Check both the final URL (including `/security/twofactor/reauth/`) and visible text such as `2FA Entry`, `Confirm it's you with your passkey`, or `Try another way`; generic `Log in` regexes alone miss this state. A redirect away from the requested Business URL with zero assets is not proof that access was lost: capture the final URL, title, and a short sanitized body excerpt, classify the reauth gate, and stop before any write.

For manual reauthentication, keep the protected persistent profile under an exclusive lock and open a headed localhost-only noVNC session. If the canonical login helper intentionally allowlists only Meta Ad Library URLs, do not weaken that allowlist as a shortcut: start it on its permitted URL, then invoke the exact Playwright Chromium executable with the same `--user-data-dir` and `--no-sandbox` to forward the Business Settings URL through Chromium ProcessSingleton. Require the marker `Opening in existing browser session.` before asking Rodolfo to complete passkey/2FA in the visual session; never request credentials in chat.

For an explicitly authorized batch, checkpoint every account independently and persist unique IDs before continuing. Meta list rows are virtualized, `selected_asset_id` is not necessarily the real Ad Account ID, and an error modal can be ambiguous about whether the write committed. Never retry an ambiguous creation until a before/after asset-ID readback proves that no new account appeared. Do not randomize timing to simulate a human or evade activity controls; use a transparent fixed cadence and stop on any security/restriction gate. Direct person assignment is a separate permission change: if an account is BM-owned but shows `0 people`, report the gap and get the required confirmation before assigning anyone.

For long-running batches, keep Rodolfo informed without streaming raw logs. Default to a concise progress checkpoint after authentication/preflight, every five confirmed creations, and immediately on any pause, retry, block, or stop; if he asks for a tighter cadence, report after each confirmed account when the platform permits controlled in-thread updates. Every checkpoint must state `Criadas X/Y`, `Faltam Z`, and the current state. A partial stop must clearly separate validated creations from the unattempted remainder, and automatic background-completion notifications remain disabled.

Full workflow, correct `ad_accounts` route, ProcessSingleton reuse, BM target correction, batch-safe ID reconciliation, new-portfolio limit handling, repeated generic rejection handling, and shutdown readback: `references/meta-business-ad-account-browser-creation.md` and `references/meta-business-ad-account-batch-reconciliation.md`.

## Meta Business Manager inventory / asset access audits

Use this skill not only for campaign operations, but also when Rodolfo asks to inventory a Meta Business Manager: ad accounts, people/users, pixels/datasets, pages, system users, and asset-to-account relationships.

Critical rules for BM audits:

1. **Token capability first.** Test candidate 1Password token items read-only with `me`, `me/permissions`, `me/businesses`, and a small BM/account edge. A token with `ads_read` but `business_management=declined` may read some ad data but is not sufficient for BM-wide user/asset inventory.
2. **Always paginate.** Never treat the first Graph API page as the total. BM counts can be badly underreported if you stop at the initial edge response. Page `owned_ad_accounts`, `client_ad_accounts`, `business_users`, `owned_pixels`, and `client_pixels` until no `paging.next` remains.
3. **Define “users” by surface.** `/{business_id}/business_users` returns direct BM users and can expose e-mail, but UI totals may include users assigned through assets/partners. To map operational access, scan `/{act_id}/assigned_users?business={business_id}` across every owned/client ad account and dedupe IDs.
4. **E-mail caveat — verify docs before blaming rate limit.** If Rodolfo challenges blank e-mails, check the current Meta docs and `debug_token` rather than repeating an assumption. As of Graph v25.0, the Ad Account `assigned_users` edge documents only `tasks`/`permitted_tasks` additions on AssignedUser nodes and returns `id,name,tasks`; it silently omits `email` even when requested and even with `business_management=granted`. The `email` field is documented on the `BusinessUser` node (`/{business_user_id}` / `/{business_id}/business_users`) as “User's email as provided in Business Manager.” Join e-mails only for users also present in `business_users`; otherwise leave e-mail blank and escalate to UI/internal-request extraction rather than inventing or deriving it.
5. **Pixels/datasets route.** For the Meta UI “Data Sources → Datasets & pixels” audit, use `/{business_id}/owned_pixels`, `/{business_id}/client_pixels`, and `/{act_id}/adspixels`. Dataset-named edges may be absent depending on Graph version; do not block the audit if pixel edges provide the visible data-source inventory.
6. **Throttle long scans.** A full BM traversal may require hundreds of Graph calls. Use bounded backoff/throttle and summarize final counts; do not stream raw API output into Discord.
7. **Sheets export shape.** If Rodolfo asks for a Google Sheet export, create exactly the requested operational tabs unless he asks for a summary. For this audit class, the proven tabs are `Contas x Perfis` and `Pixels x Contas`, then verify readback row counts after write.

Session-specific references: `references/meta-business-manager-inventory-sheets-2026-07-06.md`, `references/meta-bm-inventory-sheets-2026-07-06.md`, and `references/bm-audit-assigned-users-email-visibility-2026-07-06.md` (endpoint list, Sheets tab layouts, row deletion by profile, and the documented distinction between BusinessUser email visibility and Ad Account assigned_users e-mail omission).

## Meta Ads MCP Server evaluation and pilots

Use this path when Rodolfo asks whether Meta's Ads MCP Server can help Ares, connect an app directly, discover accounts/Pages, reduce Graph API wiring, or bypass verification/checkpoints.

1. **Separate discovery from authorization.** The MCP can list ad accounts and Pages already accessible to the authenticated user, but it does not verify, release, assign, or grant those assets.
2. **Never present it as a bypass.** Do not claim it replaces App Review, Advanced Access, Business Verification, user authentication, BM/Page permissions, account restrictions, or Meta checkpoints.
3. **Use an MGS-controlled app for production assets.** An app owned by a friend/vendor may demonstrate feature availability, but MGS assets should authenticate through an app institutionally owned and controlled by MGS.
4. **Ares is technically compatible.** Hermes supports remote HTTP MCP servers, OAuth, pre-registered OAuth clients, and per-server tool filtering. Validate the exact Meta OAuth flow in a pilot rather than assuming compatibility from protocol support alone.
5. **Pilot read-only first.** Compare MCP account/Page discovery, campaign inventory, and reporting against current Graph API/readback before exposing write tools.
6. **Keep writes paused and bounded.** For a controlled write, create only approved `PAUSED` objects, do not expose activation initially, verify by GET/UI, and clean partials using this skill's normal safety model.
7. **Treat endpoint isolation as a test, not a conclusion.** Because the MCP is Meta-hosted, it is a useful alternative route for the known `POST /ads` checkpoint boundary. The docs do not promise a bypass; only a controlled comparison can show whether the same `code=31` boundary reproduces.
8. **Use Meta's own controls.** Where available, enforce Business Suite Ads MCP rules for campaign creation and budget changes in addition to Hermes tool filtering and MGS authorization gates.

Detailed official-source findings, tool names, permissions, interpretation, and pilot checklist: `references/meta-ads-mcp-server-assessment-2026-07-17.md`.

## Meta Ad Library discovery and creative extraction

Use this path when Rodolfo asks to enumerate Pages, domains, ads, or creatives from a public Meta Ad Library keyword/domain URL.

1. **Choose the source by market and ad class.** The official Ad Library API is useful for structured catalogue queries, but ordinary commercial ads outside the UK/EU may not be covered. For active Brazilian commercial ads, inspect the normal Ad Library page and its rendered serialized payload first.
2. **Keep identifiers distinct.** Report the payload's `page_id` as the Page ID. A different number in `snapshot.page_profile_uri`—often beginning with `615...`—is a profile URL identifier and must not be substituted for `page_id`.
3. **Account for collation.** Search-result totals, visible cards, and unique Pages are different measures. Deduplicate on `page_id` and preserve `collation_count`/Library IDs if counting ads or versions.
4. **Inventory domains Page by Page.** Open each Page through `view_all_page_id=<page_id>`, parse every `snapshot.link_url`, and recursively inspect URL-valued query parameters such as `url=`. Report unique registrable domains separately from hostnames/subdomains.
5. **Treat API tokens correctly.** A valid Marketing API token with `ads_read` does not prove Ad Library API authorization. Probe `/me/permissions`, then a small read-only `/ads_archive` call. `code=10`, `error_subcode=2332002` means the app lacks permission for this action; do not rotate a working Marketing API token on that evidence alone.
6. **Do not expose token-bearing URLs.** `ad_snapshot_url` and Graph paging URLs can embed access tokens. Summarize IDs/counts and sanitize URLs before reporting.
7. **Set the right expectation.** The API returns structured metadata and snapshots; it is not a direct bulk JPG/MP4 download endpoint. Creative files still require individual snapshot extraction under Meta's analysis/storage terms.

Detailed field map, safe token probe, coverage boundary, payload extraction procedure, and pitfalls: `references/meta-ad-library-api-browser-extraction-2026-07-12.md`.

## Reporting format

### Executive health verdicts for Rodolfo

When Rodolfo asks whether “reports, crons, agents and campaign creation are all working,” do not answer with a credential-cutover narrative or a long inventory dump. Audit the full named operation first, then lead with one plain verdict:

- **Tudo operacional** — every required lane has a successful real tick/readback.
- **Quase tudo operacional** — normal use works, but name each remaining unproven or degraded lane.
- **Não operacional** — identify the exact blocker and affected functions.

Then summarize in at most three short groups:

1. **Funcionando:** agent/gateway, reports, enabled crons, creation/cloning and verified Discord/Meta readbacks.
2. **Ressalvas:** stale historical badges, intentionally disabled jobs, external data delay, or a lane awaiting its first real post-fix tick.
3. **Ação necessária:** say explicitly whether Rodolfo must do anything.

Keep technical health separate from campaign performance: an active, correctly reporting campaign with poor ROI is **operational but performing badly**, not an automation failure. Likewise, a prepared channel with no implemented workflow is **not broken**; label it “ainda não implantado.” Do not call a repaired cron fully green until either its own scheduler records `last_status=ok` and `failure_streak=0`, or clearly label the distinction between a successful manual recovery and the pending real tick.

### Ares HOA gestor reports: no `ID REC` column

For HOA/checkpoint reports intended for gestores, do **not** show an `ID REC` column in the Discord table. Rodolfo corrected that this is visual pollution: the complete campaign name with its numeric suffix is already unique enough for human operation, e.g. `Elena Santana - ES - ESP - 004`.

Operational rule:

1. Keep recommendation IDs only in JSON/audit/state if needed for technical traceability.
2. The human table starts with `Nome campanha`, then `Início`, `Status`, metrics, `Ação`, and `Motivo`.
3. The header/instructions should tell Rodolfo/gestores to respond with the **full campaign name**.
4. If a response uses only a partial name and matches multiple campaigns, ask for disambiguation rather than requiring `ID REC`.

Session detail: `references/hoa-report-no-id-rec-2026-07-09.md`.

### Ares intraday / reativar-todas row visibility

Ares Meta intraday and reativar-todas Discord reports must show every candidate row in-channel/thread. Do not replace tail rows with `... +N linhas no audit local`; Rodolfo expects the operational report itself to contain all rows. If the message exceeds Discord length, split into multiple valid chunks while preserving readable fenced/table formatting.

Keep Rodolfo’s report concise and separate evidence from interpretation:

```text
Teste                         Resultado
----------------------------  -----------------------------------
Proxy validado                IP mudou de Hetzner para ISP/proxy
Dry-run                       OK
Campaign PAUSED               OK
Adset PAUSED                  OK
Adcreative por video_id       OK
POST /ads                     Falhou code/subcode
Cleanup                       DELETED verificado

Conclusão: [IP confirmado / IP descartado como único fator / endpoint-specific block]
```

## References

- `references/webshare-adspower-meta-post-ads-proxy-test-2026-06-18.md` — session-specific diagnostic: Webshare proxy from 1Password, direct vs proxied egress, dry-run/write results, cleanup, and conclusion for `POST /ads` block.
- `references/advanced-access-app-token-post-ads-2026-06-18.md` — session-specific diagnostic: new Advanced Access Meta app/token still reproduced the same `POST /ads` checkpoint while campaign/adset/adcreative creation and cleanup worked.
