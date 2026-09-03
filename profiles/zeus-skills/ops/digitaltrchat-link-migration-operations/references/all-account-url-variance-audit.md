# Read-only all-account URL variance audits

Use this procedure when Rodolfo supplies one or more exact DigitalTRChat logins and asks whether Page URLs differ across every segurador/account and Page. This is an inventory and comparison task, not migration authorization.

## Scope model

For each exact login:

1. Resolve the exact 1Password item by the login field; keep the credential only in process memory.
2. Enumerate every imported account and deduplicate repeated responsive-layout DOM entries by `(account_id, normalized account_name)`.
3. Preserve accounts with zero Pages and logins with zero imported accounts in the final partition.
4. For each account, activate its exact `account_id`, reload Bot Manager, and enumerate every visible Page as `(DTR Page ID, Facebook Page ID, Page name)`.
5. Audit only the surfaces Rodolfo named. For the common link check these are Get Started, No Match, and every existing Auto Principal Drip Button/Generic Template URL. Persistent Menu is out of scope unless explicitly requested.

A login is a credential container, not a segurador boundary. A repeated display name with two different account IDs remains two separate inventory entries.

## Identity-safe action-route discovery

Bot Manager keeps stale Get Started/No Match anchors from the previously selected Page while `/messenger_bot/get_page_details` hydrates the new Page.

- Select the exact Page row by both DTR Page ID and Facebook Page ID.
- Wait for the `get_page_details` response and a bounded hydration interval.
- Extract the direct `/messenger_bot/edit_bot/<id>/1/getstart` and `/nomatch` routes.
- Open both routes read-only and require hidden `page_table_id == DTR Page ID` and `page_id == Facebook Page ID`.
- A route count of one is not enough: if identity is stale, reselect/reload and retry. Never include a stale Page's URLs in another Page's signature.
- Classify zero action routes separately from an identity mismatch; do not collapse either into “same URLs.”

## Account-safe Flow Builder reads

- Keep one authenticated context pinned to one imported account while auditing its Pages. Do not switch that context to another account while Page tasks are running.
- Open `/visual_flow_builder/flowbuilder_manager/<DTR_PAGE_ID>/1`, wait for DataTable hydration/pagination, and require the exact `Auto Principal Drip` yellow Edit action.
- Parse `window.data`; screenshots and visible canvas nodes are incomplete.
- Inventory every HTTP value in Button `value`/`text` and Generic Template `imageClickDestinationLink` fields. Preserve occurrence counts because one semantic destination may appear in multiple fields.
- Record node/edge/reachability totals, but do not classify a missing flow as a URL difference. Use a separate `flow_absent` disposition.

Concurrency is safe only inside a context whose imported account will not change. Limit concurrent Page readers; serialize account switching.

## Exact variance signatures

Build independent exact signatures for:

- Get Started URL multiset;
- No Match URL multiset;
- Auto Principal Drip URL multiset, including repeated occurrences;
- the combined three-surface Page signature.

Ignore node IDs and visual ordering in URL signatures, but do not normalize domains, paths, tracking parameters, duplicate query parameters, or platform-added subscriber suffixes. Those are precisely the differences under audit.

For parsing only, replace literal `#PAGE_ID#` with a sentinel before using standard URL parsers, then confirm the original token is unchanged. Parse semantic labels from the original full string so the first `#` does not hide later `utm_content` values.

Group signatures per imported account first. Cross-account differences can be legitimate site/country/language variants; never label one “wrong” without an approved destination authority. Report exact minority/outlier Page IDs and representative hosts/paths.

## Disjoint result partition

Every enumerated Page must land in exactly one bucket:

- `complete`: Get Started, No Match and AutoDrip read with exact identity;
- `action_only_no_flow`: action URLs exist but AutoDrip is absent;
- `no_actions_no_flow`: neither action routes nor AutoDrip exists;
- `partial_error`: a retrievable surface failed after bounded retries;
- `identity_conflict`: editor IDs do not match the Page;
- `flow_ambiguous`: zero/multiple flow rows after full table inspection.

Keep “uniform absence” distinct from “uniform URLs.” A segurador whose Pages all lack AutoDrip has no internal AutoDrip variance, but it is not a healthy or complete configuration.

Reconcile totals programmatically:

- requested logins = collected logins;
- account inventories = processed + zero-Page accounts;
- total Pages = sum of the disjoint Page buckets;
- per-surface available + missing = total Pages;
- enumerated group counts must equal declared totals.

## Resumability and recovery

Large audits can exceed one foreground execution window. Persist one JSON artifact per login and checkpoint after each completed imported account; resume by exact account ID instead of restarting or silently losing progress.

Transient credential-provider or network errors get bounded retry after confirming the operation is read-only. Do not cache or persist credential values. If action routes were initially stale, preserve only the corrected identity-validated result as active output while retaining the earlier attempt as audit evidence when useful.

## Reporting

Report, without implying correctness:

- requested/collected logins;
- imported accounts, zero-account logins, and zero-Page accounts;
- total Pages and the disjoint completeness partition;
- accounts with more than one exact URL signature;
- majority/minority groups with exact Page IDs;
- missing action/flow Page IDs;
- duplicate query parameters and other literal URL anomalies;
- graph depth differences such as legacy M00–M15 versus M00–M28;
- identity mismatches and unresolved failures;
- explicit `production_writes = 0`.

A read-only variance audit authorizes no correction. Wait for Rodolfo to identify the destination authority and target scope before writing.
