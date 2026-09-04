# Vendor Skill Evaluation and Read-Only Pilot

## When this reference applies

Use after a video, post, repository, or vendor announcement suggests Agent Skills for a live system such as Google Ads, Analytics, Cloud, or another operational platform.

## Core sequencing correction

Do not choose or install skills from the marketing/demo surface first. The correct order is:

1. Confirm the primary vendor source and current repository state.
2. Define the target business outcome and owner.
3. Establish least-privilege, corporate access to the real account or platform.
4. Run a read-only inventory of the live structure, data, enabled features, and actual gaps.
5. Map those gaps to the smallest useful set of vendor skills.
6. Inspect every candidate skill for prerequisites, auth assumptions, conflicting directives, stale versions, and write behavior.
7. Adapt the selected workflow to MGS governance where generic vendor instructions conflict.
8. Pilot on one account/property with read-only permissions, validate real queries, then decide whether to expand.

## Source validation

- Treat shared media as a discovery lead, not the authority.
- Verify the official repository, vendor documentation, license, current paths, and current install syntax.
- Counts such as “132 skills” are snapshots and can drift; count current manifests programmatically when the number matters.
- Use Hermes' native `hermes skills inspect <identifier>` before installation. Inspection success proves discoverability only, not operational compatibility.
- Do not bulk-install a repository merely because it is official. Official skills can still be irrelevant, generic, outdated, or written for another agent harness or evaluation sandbox.
- Distinguish the official source from any third-party page that packages it into an ebook, mentoring, community, or other sales funnel.

## Live-account discovery before selection

The first audit should answer:

- Is the target an individual account, manager account, organization, property, or hierarchy?
- Which child accounts/properties are active and in scope?
- Which APIs, integrations, conversion/tracking systems, reports, and write surfaces are actually used?
- Which credentials and permissions already exist in the approved corporate secret store?
- What can be learned read-only before any production mutation?
- Which analysis needs native API/MCP tooling versus browser-only inspection?

Do not infer needed skills from catalog descriptions alone. Select from observed account structure and concrete operational questions.

## Least-privilege access pattern

- Prefer an existing approved corporate technical identity over a personal login when the provider officially supports it.
- Start with read-only access at the highest relevant manager/container level only when that is necessary to inventory descendants.
- Store tokens, keys, and secrets only in the approved secret manager; never ask Rodolfo to paste them into Discord.
- Reuse an existing credential only when its scope and security model fit. Creating, rotating, or altering a production key/token follows the Critical Subset gate.
- Keep billing, budget, campaign writes, permission administration, and destructive actions outside discovery.

## Google Ads application pattern

For a Google Ads audit before skill selection:

1. Determine whether the target is a Manager Account (MCC) or an individual customer account.
2. Prefer the official Google Ads service-account workflow for MGS-owned accounts. Grant the approved MGS Service Account `Read-only` access in **Admin → Access and security**; use MCC level when descendant inventory is intended.
3. Verify a Google Ads developer token exists and has sufficient production query access. Keep it in 1Password, never in chat or source files.
4. Record the login customer ID and target customer IDs without treating those identifiers as credentials.
5. Validate access with a real `listAccessibleCustomers` request, then enumerate enabled non-manager clients before broader reporting queries.
6. Inventory campaigns, ad groups, ads/assets, budgets/bidding strategies, conversion actions, keywords/search terms, audiences/placements, geo/device/time segmentation, policy errors, change history, tracking/UTMs, and comparative performance windows.
7. Only after the inventory, evaluate candidate skills such as account diagnostics, MCP setup, API quickstart, or Analytics reporting.

Service-account authentication can remove the need for a personal OAuth refresh-token flow. Do not import a generic skill's five-credential assumption unchanged when current official provider documentation and MGS architecture support service accounts.

## Candidate classification

For each candidate, classify:

- **Needed now** — directly serves an observed live-account requirement.
- **Useful later** — valid but has no current consumer or prerequisite.
- **Reject** — irrelevant, duplicates an MGS playbook, conflicts with policy, assumes unavailable tooling, or contains unsafe write guidance.
- **Adapt** — useful core logic but auth, source, output, or approval gates must be rewritten for MGS.

Inspect at minimum:

- trigger and description accuracy;
- required tools, runtimes, MCP servers, APIs, and referenced files;
- credential model and secret handling;
- read versus write behavior;
- hardcoded API/runtime versions;
- forced output formatting unrelated to the user's request;
- sandbox-specific claims presented as universal runtime facts;
- compatibility with the owning agent's authority and canonical sources.

## Pilot acceptance criteria

- Exact target account/property and technical identity are confirmed.
- Read-only access is proven by a live API or MCP query.
- No campaign, budget, billing, conversion, permission, or production object was changed.
- The selected skill set is minimal and every skill has a named observed use case.
- Generic vendor instructions have been reconciled with MGS authentication and governance.
- A representative diagnostic/report completes with real data and readback.
- Expansion to other accounts or write capabilities remains a separate authorization decision.

## Pitfalls

1. **Catalog-first selection** — choosing skills from a demo before seeing the account creates speculative tooling. Fix: access and inventory first.
2. **Skill-equals-access fallacy** — installing instructions does not provide credentials, tools, MCP, or API enablement. Fix: validate every layer independently.
3. **Official-equals-safe-for-MGS assumption** — vendor ownership does not guarantee policy fit. Fix: inspect and adapt.
4. **Bulk installation** — importing dozens of irrelevant skills increases routing noise and maintenance. Fix: install only the audited minimum.
5. **Personal OAuth by default** — generic quickstarts often assume browser consent and refresh tokens. Fix: prefer the approved corporate service-account workflow when officially supported.
6. **Read-only promise without permission proof** — prose is not a guardrail. Fix: assign read-only access and verify the effective account role before querying broadly.
