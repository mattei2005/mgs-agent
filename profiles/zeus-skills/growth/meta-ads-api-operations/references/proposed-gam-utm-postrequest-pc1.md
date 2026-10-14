# Proposed post-request GAM UTM preparation — pending review

Status: proposal only; not an active Campaign Ops rule or execution authorization.
Owner: Rodolfo Mattei; execution design for Ares.
Source: Discord thread 1559932317861158993, initial message 1559938326063091775 and corrections 1559940089424125953 and 1559940833430474907.

When resuming this design discussion, preserve Rodolfo's requested ordering:

1. Complete and validate the manager's authorized campaign creation/duplication request, including exact destination links and campaign/adgroup UTMs.
2. Send the normal request-completed response to the manager first. Do not turn the browser step into a prerequisite for this reply or anchor its dispatch to the campaign's scheduled start.
3. Only afterward, run the proposed separate background follow-up on PC1 without extending the original campaign scope, budget, strategy or start time.
4. Process destination URLs sequentially. For each distinct destination and exact UTM pair, create a new tab; never navigate an existing processing tab to the next URL.
5. Confirm an actual network advertisement is rendered and visible. Start the 20-second observation only after that confirmation, keeping the ad in the visible viewport and the tab active. Page-open time alone is insufficient.
6. After the observation, close that exact processing tab and verify closure; preserve unrelated browser tabs/windows. Then process the next URL in another new tab.
7. If an ad does not appear, wait one minute before retrying that URL in a fresh tab. Retry cardinality is not yet approved; avoid unbounded loops and preserve per-URL results. Current global failure/loop stop limits still apply.
8. Only after every link succeeds, send one success follow-up in the original manager request thread confirming links opened and network ads visibly observed for at least 20 seconds each. Claim only that evidence, not GAM registration without independent registration readback.
9. Route ANY problem in this separate PC1 follow-up to the coordination thread 1559932317861158993, never to the manager request thread. Include the original request link, affected account/campaign/destination and exact UTM pair, confirmed progress, failure evidence, attempts and current recovery/blocker. This covers missing ads, browser/PC1 access, lease contention, navigation, timing, closure and other operational errors. Do not send a partial-success or pending-link report to the manager thread; preserve the normal campaign-completed reply already sent there. The one-minute no-ad retry still applies; reporting the issue here does not cancel safe recovery within the approved scope.

Rodolfo describes Ciro's technology as registering utm_campaign/utm_adgroup after at least 20 seconds of ad visibility within a session. This is user-provided behavior, not independently verified. Confirm with Ciro the session semantics for distinct tabs, an approved test/registration route and IVT handling before rollout. Do not manufacture clicks, change ad-block/security settings or bypass restrictions.

No handoff to Ares or runtime/script/scheduler activation has been authorized in these messages; Rodolfo requested the revised flow for review first.
