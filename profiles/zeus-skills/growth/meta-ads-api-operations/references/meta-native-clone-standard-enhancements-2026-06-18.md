# Native clone fidelity and legacy creative compatibility

## Establish the acceptance contract before testing

1. Resolve the exact source, target account, approved request, existing partial IDs and canonical executor. Preserve the source and recover only missing target layers.
2. Interpret “same creative” as the requested media, copy and configuration, not mandatory equality of an immutable `creative_id`. Verify post identity separately when social proof must be preserved; lineage alone does not prove it.
3. Freeze the new campaign number and every dependent tracking value. When UTMs belong in Website URL, require the new values there; a correct effective click URL obtained through a separate `url_tags` override does not satisfy that storage requirement.
4. Define one joint acceptance test: inherited settings, media/copy, the updated Website URL and the original budget/bid/status/schedule contract must all pass on the same target. Preserve complete expectations independently of a reduced transport payload so omission cannot silently weaken QA.

## Diagnose the failing layer

1. Reconcile all materialized IDs before retrying. Prefer the canonical engine's explicit-ad representation for a populated clone: shallow campaign/adset copies followed by source-linked ad copies. This isolates the failing layer without duplicating existing shells or depending on synchronous bulk-copy limits.
2. Compare the exact outgoing payload with the live source. Treat a legacy `standard_enhancements` rejection as a creative compatibility boundary, not proof of a global token/IP failure or universal inability to clone.
3. Keep a compact hypothesis ledger: changed input, endpoint, sanitized error, returned IDs, reconciled live IDs and unmet acceptance criteria. Check the documented field semantics and creative subtype before submitting a candidate: a field's presence in an SDK is not proof that it supports the intended override. Classify missing-Page, ambiguous-object and organic-versus-unpublished-story errors as malformed or inapplicable probes, not evidence that the original fidelity requirement is impossible. Select a new test only when material evidence distinguishes it from rejected attempts; a version change alone is not a repair rationale. Evaluate provider outcomes independently of wrapper exit codes, because a diagnostic script can exit successfully while every API candidate was rejected.
4. Do not substitute a different source campaign, disable enhancements, clear the whole feature block, relocate tracking or edit the shared source merely to pass creation. Those change the approved result rather than repair the failing representation.
5. Label results precisely: request accepted, object created, inherited settings preserved, target tracking verified, common-path integration installed, or original request completed. Never promote success at one layer to another.

No general workaround for legacy enhancements is established by this diagnostic procedure. Keep unsuccessful hypotheses in request evidence, not in a reusable recommended-fix recipe.

## Use a UI control only for the unresolved question

1. Read the earlier control's final receipt first. A manual duplicate retaining the original Website URL proves preservation only; it does not prove compatibility with a changed Website URL.
2. If a UI comparison is genuinely needed, use an existing approved session, verify the actual actor and target account/Page, and check Page ad-creation access before preparing a write. A Chrome profile label or accessible ad account is not enough.
3. Separate a browser Page-access warning from the original API error. It blocks that UI control only; it does not invalidate the API token or establish the desktop as a prerequisite for API recovery. Do not ask for another login when authentication is already valid and the missing capability is Page authorization.
4. Use the shared desktop lease and an owned tab. Inspect without changing source inputs. Test only an already authorized paused target through its recorded execution scope; do not silently introduce a parallel Campaign Ops writer or new shells.
5. An enhancement absent from the inspected UI, or an API preview marked ineligible, does not authorize changing an explicit source enrollment. Report the distinction between configured state and actual applicability without treating it as a proven normalization workaround.
6. Cancel inspection-only modals without Save/Publish, close only owned tabs, restore the prior window and release the lease in `finally`. Verify cleanup independently of the application result.

## Proven Messenger subtype restoration

Use this branch only when a source Messenger ad's returned AFS omits a required CTA subtype and its canonical or historical payload proves the intended value.

1. Keep the existing target campaign/adset IDs PAUSED and enumerate their ads before writing missing source-linked slots.
2. Preserve live `object_story_spec`, the complete AFS video/title/body/description/label/rule package, tracking, supported feature controls and Messenger JSON. Remove output-only `reasons_to_shop` and `shops_bundle` from the outgoing AFS.
3. If Graph exposes `call_to_action_types=["APPLY_NOW"]` but omits `call_to_actions`, restore `call_to_actions=[{"type":"APPLY_NOW","value":{"app_destination":"MESSENGER"}}]` from the approved operation builder, never from a guessed default. The Eggbev builder is `ares_campaign_v3/eggbev_create.py`.
4. Submit the normalized payload as `creative_parameters` on the source ad's `/copies` edge with the existing destination adset and `status_option=PAUSED`, through the canonical engine. Journal each receipt before advancing and normalize only the copied display name when needed.
5. Read back hierarchy, exact counts, lineage, status/issues, budget/bid, targeting/attribution, Page/pixel/event, copy/CTA/tracking/JSON and unchanged source. New technical media/creative/post IDs require equivalence checks, not an automatic mismatch verdict or a social-proof claim.
6. Compare rematerialized variants by labels, dimensions and binary hashes or decoded frames. Use an ephemeral Page token derived from the approved advertiser when the User token omits video `source`; never persist that token or signed media URLs.
7. Accept extra returned feature flags as disabled defaults only when every required source flag is preserved and every extra flag is `OPT_OUT`. Keep configured status, review state and actual delivery as separate findings.

## Map API fields from completed copies before escalation

When Rodolfo asks what a returned API field corresponds to, use an already-completed real source/copy pair before proposing vendor support. Resolve immutable source/target ad and creative IDs through the sealed manifest and CONFIRMED materialization journal; a COPY label or matching name alone is not lineage. Compare four layers separately: creation-time source snapshot, sealed input, effective emitted parameters, and fresh source/copy GETs. Reconstruct an effective payload only with the executor's pure functions and match its digest and canonical request-body digest to the historical receipts before calling it the confirmed request. Never replay POSTs to obtain that proof.

Mask URLs, identifiers, hashes and text with explicit stable aliases before persisting shareable payloads; keep enum names, field paths and absence states intact. Do not store raw token-bearing previews or pagination links. Compare corresponding media paths before using fallbacks: a changed top-level video_id and an unchanged object_story_spec.video_data.video_id are separate observations, not proof of changed rendered bytes. Use actual creative structure rather than IMG/VIDEO in campaign names to classify media.

Build a field dictionary with separate evidence levels: explicit documented UI label, documented semantics without a confirmed label, and unmapped. Record provider preview descriptions and eligible/ineligible/missing transformation independently. Extra OPT_OUT fields in GET and omitted source fields must not be presented as extra human toggle actions or as OPT_OUT by absence. Existing copies with accepted omissions are not a one-variable UI experiment; report remaining mapping gaps instead of inventing a control for every returned flag. This read-only mapping request does not authorize new copies, feature toggles or edits of the source.

## Reporting and stop conditions

Explain a stalled repair once in plain language: what must remain equal, which change triggers rejection, what the last real test proved and what remains unproven. Avoid repeating the full error history or asking the user to restate the same request. If no method satisfies the contract, say so directly and identify the smallest demonstrated access, authority or vendor dependency; do not present an untested UI comparison as an established cure or infer that only the vendor can fix it from unsuccessful local probes.

When vendor escalation is proposed, prepare the smallest valid reproduction and separate it from malformed exploratory requests. Describe support as an escalation, not a working repair. Inspect any new terms or consent boundary before submission and obtain the applicable authorization rather than silently accepting them. Distinguish a local draft, an opened support page, a submitted request and a real case: claim submission only with a case handle and exact readback. Keep campaign recovery pending until the original acceptance test passes, regardless of support activity.

A failed write does not authorize cleanup. Preserve partial IDs and keep targets non-delivering; delete/archive only under separate applicable authorization and confirm the terminal state by GET.
