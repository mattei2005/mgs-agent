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

Project deletion and permanent 1Password deletion may require the human admin UI. Report them as pending until independently verified; never call the cutover complete based on an instruction alone.
