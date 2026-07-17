# Canonical Google Cloud/Workspace cutover for MGS agents

Use this reference when consolidating Drive, Sheets, Gemini and agent runtimes into one company-owned Google Cloud project. It captures the reusable cutover pattern validated in July 2026.

## Target architecture

```text
Human administrator      Company Google Workspace account
Google Cloud project     One stable, intentional project ID
Technical identity       One least-privilege Service Account
Drive storage            Shared Drive with direct Manager/organizer membership
Secrets                   1Password; no JSON/token in chat, Git or local backups
Runtime auth              Service Account only; personal OAuth is not fallback
```

Project display names can change; Project IDs cannot. Reject random generated IDs before building integrations.

## Safe order of operations

1. Inventory all consumers before editing: scripts, wrappers, cron/systemd, profile jobs, skills, configs, `.env`, 1Password metadata and Shared Drive permissions.
2. Classify matches as active dependency, reusable procedure, historical/audit evidence or secret material. Never erase append-only audit history merely to make searches return zero.
3. Create the company project, enable Drive and Sheets APIs, and create a Service Account without broad Owner/Editor roles.
4. Add the Service Account directly to the canonical Shared Drive at the minimum capability that preserves the contract. Use Manager/`organizer` only when move/delete/retention operations require it.
5. Store the Service Account JSON in 1Password under a generic company item. Confirm the runtime field name by readback; attachments are not automatically equivalent to a concealed field.
6. Grant `roles/serviceusage.serviceUsageConsumer` when consumers send `x-goog-user-project`. Diagnose this separately from file sharing: calls without the quota header can prove file access, while calls with it prove IAM/quota attribution.
7. Migrate shared helpers and every consumer to one item/env contract. Remove personal OAuth fallback from active code only after the Service Account passes token, Drive and Sheets canaries.
8. Run bounded canaries, then remove old scripts, local token files, paused jobs, 1Password items and obsolete Drive members. Validate absence by readback and a second active-code scan.
9. Preserve historical references only when clearly marked `Historical / superseded / do not execute`.
10. Update infrastructure inventory, audit log, checkpoint and REPORT-INFRA.

## Consumer coverage and exact-runtime proof

A credential catalog or generic API canary is not a complete consumer inventory. Search every operational execution surface, including:

- `/root/mgs-agent/scripts/` and wrappers referenced by cron/systemd;
- `skills/**/scripts/` and any project-local production skills;
- live profile scripts and versioned profile mirrors;
- config/env selectors, 1Password item titles and hard-coded model IDs.

Classify `tmp/`, caches, imports, analysis packs, audit logs and dated evidence separately so historical matches do not hide active ones or trigger destructive cleanup.

After a generic Drive/Sheets/Gemini canary passes, run the **exact real consumer** that was migrated. For Gemini this must verify both independent selectors: the 1Password item title and the model endpoint. A valid new key can coexist with an operational script still pointing to the old item or old model. Exercise the consumer's full dependency chain, validate the produced artifact, then delete the canary. Check declared external commands/packages before the run; if setup is missing, install or configure the dependency through the authorized infrastructure path and rerun the real consumer instead of treating the generic API response as completion.

### Identity-specific Sheet manifest

A successful Sheet inventory belongs to the exact Service Account email that was tested. When the project or Service Account changes, prior `18/18` or similar results do not transfer to the replacement identity.

1. Preserve a named manifest of every in-scope Sheet, including on-demand finance files and My Drive files kept in place to preserve IDs/forms/formulas.
2. Probe each manifest entry with the replacement identity on both APIs: Drive `files.get` and Sheets `spreadsheets.get`, with quota attribution where required.
3. Treat Drive 404 plus Sheets 403 after an identity replacement as a likely file-level sharing gap, not proof that the APIs or Shared Drive are unhealthy.
4. Do not infer portfolio coverage from the Shared Drive root, a disposable Sheet, or the subset of hard-coded IDs found in current scripts. On-demand files may be known only from the canonical workflow manifest/checkpoint.
5. Keep the old identity until every manifest row passes, unless Rodolfo explicitly accepted no rollback. If the old identity was deleted first, reopen the cutover rather than recording completion.

### Safe consumer probes

Before executing a supposed dry-run or `--help`, inspect the script's entry point and mode gates. Some legacy one-shot scripts execute API calls at module import, ignore `--help`, or write local state/reports even when external writes are disabled. For long portfolio scans:

- confirm the exact interpreter/wrapper used by cron;
- verify which side effects are gated by `--apply` and which logs/state/backups are not;
- use real bounded flags such as user/account/page limits rather than inventing `--dry-run`;
- set a timeout only after estimating the full portfolio duration;
- after timeout, confirm no process remains and classify the result as partial;
- never convert zero errors observed before timeout into a completed PASS.

## Drive + Sheets canary

Use a disposable Google Sheet inside the Shared Drive:

1. Obtain one token with Drive + Sheets scopes.
2. Create the Sheet under the canonical Shared Drive root.
3. Resolve the real initial tab title from Sheets metadata; do not assume `Sheet1` or `Canary` because localization changes it.
4. Write a small sentinel range.
5. Read it back exactly.
6. Update a bounded cell/range and read it back exactly.
7. Delete the canary in `finally` and require Drive HTTP 204.
8. Report a sanitized file-ID digest, HTTP statuses and exact-readback boolean; never print tokens or credential JSON.

If reporting code fails after the remote operations, verify deletion separately before retrying. Stop after repeated failures instead of creating a canary loop.

## `.env` and backup safety

- Shell-sourced `.env` values containing spaces must be quoted:

```text
MGS_GOOGLE_SERVICE_ACCOUNT_ITEM="Google Service Account - MGS Agent"
```

- Validate with `bash -n` and sanitized environment readback.
- Never pass `.env` to a generic patch that may emit surrounding lines in its diff.
- Never copy `.env` into a rollback directory. Back up only code/config; verify the backup tree contains no secret-variable markers.
- If a tool trace includes credential-bearing context, treat the credential as potentially exposed even when `.env` is Git-ignored: contain copies, record the incident and rotate the token through an explicitly authorized sequence.

## Gemini API keys — current flow

Authoritative docs: <https://ai.google.dev/gemini-api/docs/api-key>

Google's current Gemini flow distinguishes standard keys from authorization keys:

- Create new Gemini authorization keys in **Google AI Studio**, not the generic Cloud Console key form.
- Existing Cloud projects must first be imported in AI Studio: Dashboard → Projects → Import projects.
- New AI Studio keys are bound to a Service Account and restricted to the Gemini API by default.
- Do not force `Generative Language API` into the generic Cloud Console API-restriction selector; current Google documentation explicitly directs Gemini-only keys to AI Studio.
- If Workspace blocks AI Studio, enable **Google AI Studio** under Admin Console → Apps → Additional Google services → Service status for the authorized organizational unit.
- Authorization keys may not use the legacy `AIza` shape or 39-character length. Validate by a real models/API response, not by prefix/length assumptions.
- Apply IP/application restrictions only after confirming the actual stable egress path for every runtime.

## Gemini billing gate

A valid key and HTTP 200 model catalog do not prove generation quota. Run a disposable image canary. A 429 containing free-tier request limit `0` means generation requires a paid plan/billing; it is not an invalid key.

Billing is a separate critical change. Stop and obtain explicit authorization that names:

- billing account;
- target project;
- monthly budget/alert threshold;
- post-change image canary and cost-monitoring expectation.

Do not silently downgrade models to bypass billing or quota. A model change is a scope change.

## Destructive cleanup gates

Before removing old access or credentials, require:

- new Service Account token PASS;
- Drive root capabilities PASS;
- Sheets metadata through `x-goog-user-project` HTTP 200;
- create/write/read/update/delete canary PASS;
- bounded runtime consumer tests PASS;
- replacement human admin and technical Manager membership confirmed.

After cleanup, validate:

- old secret files absent;
- old jobs absent from profile job stores;
- old 1Password item absent from active vault listing (note CLI deletion may leave it in Recently Deleted);
- old human/Service Account absent from Shared Drive permissions;
- active scripts/config contain zero old item names, OAuth paths, old emails or old Service Account identities.

Project deletion and permanent 1Password deletion may require the human admin UI. Keep the evidence level explicit and do not overstate what automation proved.

## Closing human-only deletion gates

When an external cleanup is visible only in a human administrator UI, distinguish three evidence classes:

1. **Automated readback** — API/CLI returns the actual lifecycle/deletion state. This is independently verified.
2. **Partial automated corroboration** — for example, `op item get` confirms an item is absent from the active vault, but a service-account CLI cannot inspect **Recently Deleted**. Record exactly what was corroborated; absence from the active vault does not prove permanent deletion.
3. **Human administrator confirmation** — Rodolfo confirms the state after checking the authoritative UI. This can close the manual action operationally, but inventory, checkpoint and audit must label it `manually confirmed`, not `API verified` or `independently verified`.

Closure procedure:

- identify the exact user message that confirms the UI action;
- run every non-mutating corroboration available without exposing credentials;
- if an API needed only for verification is disabled, do not enable it merely to obtain a cleaner readback unless that state change is separately requested/authorized;
- preserve protected resources explicitly (for example, record that the canonical project was retained);
- clear the operational pending list only when the manual action itself is confirmed, while retaining the verification limitation in structured evidence;
- update inventory, checkpoint and append-only audit with the confirmation source and evidence class;
- send the final REPORT-INFRA and validate its Discord message readback;
- report the outcome as “closed with manual external confirmation” when direct automated proof is unavailable.

Never translate a short confirmation such as “feito” into stronger technical evidence than the source supports. Resolve it against the immediately preceding requested actions, record those actions precisely, and state any readback limitation concisely.
