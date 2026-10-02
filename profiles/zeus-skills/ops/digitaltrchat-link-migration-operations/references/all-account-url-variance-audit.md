# Read-only all-account URL variance audits

Use this procedure when Rodolfo supplies one or more exact DigitalTRChat logins, or asks to inspect every Page in all DTR containers. This is an inventory and comparison task, not migration authorization.

## Scope model

Choose the denominator before logging in:

- Exact logins named by Rodolfo → only those exact usernames.
- “All DTR” / “every DTR Page” without a login restriction → every unique DigitalTRChat username in the current 1Password DTR metadata map. Do not substitute active Sheet users, a prior audit population, or a brand-name subset; those are narrower scopes unless Rodolfo explicitly requests them.

For each selected login:

1. Resolve the exact 1Password item by the login field; keep the credential only in process memory.
2. Enumerate every imported account and deduplicate repeated responsive-layout DOM entries by `(account_id, normalized account_name)`.
3. Preserve accounts with zero Pages and logins with zero imported accounts in the final partition.
4. For each account, activate its exact `account_id`, reload Bot Manager, and enumerate every visible Page as `(DTR Page ID, Facebook Page ID, Page name)`.
5. Audit only the surfaces Rodolfo named. For the common link check these are Get Started, No Match, and every existing Auto Principal Drip Button/Generic Template URL. Persistent Menu is out of scope unless explicitly requested.

For global scope, assert programmatically that the collected username union equals the selected 1Password username union before reporting completeness. A login is a credential container, not a segurador boundary. A repeated display name with two different account IDs remains two separate inventory entries.

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

## Fast direct read protocol

Use the authenticated DTR session's request client for large read-only inventories; do not render one full manager UI per Page when the same identity-safe data is available through the app's own endpoints.

1. Pin one authenticated browser context to one imported account. Never switch that context while any Page request is running.
2. For each Page, `POST /messenger_bot/get_page_details` with `page_table_id=<DTR_PAGE_ID>` and `media_type=fb`. Parse `action_buttons_str` for the exact `/messenger_bot/edit_bot/<setting_id>/1/getstart` and `/nomatch` routes.
3. `GET` each action editor and require hidden `page_table_id == DTR Page ID` plus `page_id == Facebook Page ID` before accepting any URL.
4. `POST /visual_flow_builder/visual_flow_builder_data/<DTR_PAGE_ID>` with a normal DataTables payload and `length` large enough to cover every row. Match the reference name `Auto Principal Drip` exactly; keep zero, one and duplicate rows distinct.
5. For each exact match, derive `/visual_flow_builder/edit_builder_data/<builder_id>/1/fb`, `GET` it, parse the serialized `var data` graph, and inventory every URL-bearing Button and Generic Template field. The manager HTML alone has only an asynchronously hydrated shell.
6. Run Page reads concurrently only inside account-pinned contexts. For a large login, separate contexts may process different accounts concurrently if each context logs in, switches once, remains pinned, and every action/flow read still passes Page identity validation.

Checkpoint after every completed account, not only after a whole login. If the foreground window ends, resume by exact `(login, account_id, normalized account_name)` and never replay completed accounts. Sharding is safe only at login/account boundaries; merge shards in code and assert unique login, account and Page unions before reporting totals.

## Literal prefix scans

For “starts with” audits, decode transport-only HTML/JSON slash escaping for comparison, then match the supplied prefix case-insensitively while preserving the original URL bytes in evidence.

- Count URL occurrences as well as distinct Pages; one Page can contain the same destination in Get Started, No Match, a Button and an image-click field.
- Never strip a closing `]`, `}`, `)` or `#...#` token from a captured URL merely as punctuation—tracking placeholders such as `[utm_content]` and production placeholders can legitimately end there.
- Report every requested prefix, including explicit zero-result prefixes, and reconcile prefix occurrence totals to the per-surface total.

## Vertical classification after a prefix scan

A prefix scan identifies current legacy destinations; it does **not** classify the Page's country/vertical/language by itself. When Rodolfo next asks which vertical the matched Pages belong to:

1. Freeze the exact matched population as `(login, account_id, DTR Page ID, Facebook Page ID, Page name, matched prefix)` before consulting another surface.
2. Join each Page to the approved Page-classification source by exact DTR Page ID and cross-check the Facebook Page ID. Read Google Sheets only through the canonical Service Account. Do not use a login title, current URL, `utm_term`, Page name, or SB template as destination authority.
3. Inspect the live tab schema independently. One tab may expose explicit `pais + vertical + lingua`, while a blocked/on-hold tab may retain only identity and a template label. Do not report a template-derived value as if explicit classification fields were present.
4. Use four disjoint confidence classes:
   - `confirmed`: one exact authoritative Page row plus explicit classification fields, or a Rodolfo-approved legacy-route exception that applies to this exact population;
   - `corroborated_not_authoritative`: container label, current `utm_term`, route family and/or one unique SB template agree, but no explicit Page-level authority was found;
   - `conflict`: authoritative/corroborating sources disagree, such as DTR URL semantics versus the unique SB template;
   - `unresolved`: no exact authoritative row and insufficient independent corroboration.
5. Treat SB as corroboration only. Join it by exact `FB_PAGE_ID`, report `sem cadastro SB` separately, and never let a template name silently override the DTR Page-classification source.
6. Reconcile `confirmed + corroborated_not_authoritative + conflict + unresolved = matched Pages`, then report the exact conflicting and unresolved Page IDs inline. A migration or catalog choice may use only `confirmed` Pages unless Rodolfo explicitly resolves or overrides another class.

For Openzed specifically, the approved `card.openzed.com → US-CC-EN` and `tarjeta.openzed.com → US-CC-ES` exception applies only to the exact audited legacy population. Pages outside the Openzed classification Sheet remain separate corroborated/unresolved records even when their container and SB template point to the same vertical; never generalize the hostname rule silently.

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
