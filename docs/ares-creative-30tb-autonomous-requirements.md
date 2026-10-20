# Ares Creative Ops — 30 TB autonomous archive requirements

## Authority and scope

- Owner: Rodolfo Mattei; Discord user 344196393512075265.
- Requirement source: https://discord.com/channels/1185714635991679006/1562078493498540042/1562086632151322735
- Related discussion: same thread; source creative audit thread 1562077031099793439.
- Approved operational requirement: managers place creative media in the existing upload folder; Ares coordinates treatment, archiving, validation, inventory reconciliation and source cleanup unattended, without routine approval per file or dependency on Rodolfo's computer.
- Target account stated by Rodolfo: mgsdigitalcorp@gmail.com, with 30 TB available according to him. Account capacity and exact destination folder have not been independently verified.
- No additional Workspace storage purchase is requested.

## Status — implementation approved; owner-created project received, setup pending

Rodolfo approved advancing with the isolated integration and preparing the limited cleanup policy in message https://discord.com/channels/1185714635991679006/1562078493498540042/1562087305051902063. This does not activate source deletion: exact targets and the destructive-activation confirmation remain pending after the pilot. The current Service Account-only agent architecture remains active.

Preparation completed locally in `integrations/creative-archive-30tb/`: copy-only Apps Script pilot, manifest and disabled destination configuration. Node syntax validation passed; 16 offline contract tests passed (not Google execution receipts). The pilot has no source-removal or scheduling primitive.

Read-only canonical Service Account probes returned HTTP 200 for MGS-AGENTS and CRIATIVOS. The source pilot candidate `1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N` is a video under `CRIATIVOS/Nicolas`, with size 5375929 bytes and MD5 `59065739912275ee5995bfee8d5ca9c7`; metadata reported `canCopy=true`. This does not prove the destination account's permission.

Historical pre-retry blocker (superseded): the isolated browser reached Google sign-in; no Google login was available through `browser_vault`, and the 1Password browser backend reported `locked` with unlock unavailable in this session. The original browser session timed out during navigation; an isolated session recovered browser access and established the real authentication gate. No password or code was requested in chat, no alternate personal token was created, and no credential was read into conversation.

Historical pre-retry metadata scan (superseded): the canonical 1Password Service Account CLI remained available. A credential-safe metadata search of accessible items did not locate a Google account Login for `mgsdigitalcorp@gmail.com`; only the canonical Service Account and unrelated Google Ads credentials were identified. No password/secret fields were read in that pre-retry scan. Do not infer that the browser backend being locked means canonical 1Password itself is unavailable.

Zeus has not created a remote Apps Script project, archive destination folder, new permission, scheduler, copy or deletion. Rodolfo subsequently supplied the owner-created project below. The exact 30 TB destination, account storage quota, script consent and canonical Service Account destination readback remain unverified.

## Latest retry — credential located; Google browser-security rejection

Rodolfo provided the Login item and authorized retry in message 1562090838748569660. The canonical 1Password item `tvo7ib7lqon66pz23j4x333jny` in vault `ghkdcenuzsp57w37nzhxuxnkj4` is titled `accounts.google.com`; username exactly matches `mgsdigitalcorp@gmail.com`, and the standard password field is populated. Only credential-safe metadata/presence was emitted; no screenshot credential was used.

Both the Google ServiceLogin and official InteractiveLogin entry paths accepted navigation, then rejected the browser immediately after account identification with `This browser or app may not be secure` (`rrk=46`). No password entry occurred, so neither a bad password nor 2FA failure is established. No temporary browser-vault credential relay was created. Stop automated login retries rather than changing security settings, routing through a third-party proxy or extracting alternate password fields.

Zeus's browser-security rejection remains unresolved; Rodolfo confirmed access through his own supported browser. This is setup only, not a computer-dependent execution architecture. The pilot remains undeployed. Prior missing-credential diagnosis above is historical and superseded by this observed provider block.

## Owner-created Apps Script project — supplied, not independently inspected

- Source message: 1562094810528088185.
- Exact URL: https://script.google.com/home/projects/1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF/edit
- Exact project ID: `1NxZ0ZTgZk4f3pzzX3fQQ-Y2wKpunjYbAaxbO8HN1fe9R5gXbEYVLpbUF`.
- Intended owner account: `mgsdigitalcorp@gmail.com`; reported by Rodolfo, not yet independently verified.
- Rodolfo reported Advanced Drive service setup complete in message 1562096306967548047; this is owner-reported, not independently inspected by Zeus.
- Next single setup step: paste and run the read-only `CheckAccount.js` function `verificarContaMGS` through the owner-supported browser and return its safe account/quota log. No file creation, copying, permission changes, triggers or source removal are in this function. Six new offline contract tests pass, and the combined pilot/preflight suite has 22 passing tests; these are not Google runtime receipts. Do not deploy publicly or enable triggers.
- Apps Script API documentation explicitly states that its API does not work with Service Accounts. Do not ask Rodolfo to share the script with the canonical Service Account as a supposed way to remotely manage or execute the script. File access through Drive and Apps Script API support are different gates. Preserve Service Account authentication for agent Drive/Sheets consumers; owner-side isolated script setup/consent remains necessary.

## Proposed isolated architecture, pending approval and proof

1. Preserve the current Shared Drive MGS-AGENTS (0AEwt4Ye690ocUk9PVA) as upload and temporary processing space; managers keep the existing entry workflow.
2. Preserve canonical agent identity mgsagent@mgs-core-prod.iam.gserviceaccount.com through mgs_google_workspace_auth.py; do not restore retired personal OAuth artifacts or change agent authentication.
3. Evaluate a separate Google Apps Script connector authorized by the 30 TB account. The connector, not the Service Account, creates archive copies owned by that account. Initial consent and exact permissions require the separate architecture/security approval before setup.
4. Ares remains the operational owner; the isolated connector provides storage operations. Do not claim Ares can directly upload binaries into personal My Drive with the Service Account.
5. Record original and processed file IDs, exact source and destination folders, size/checksum, lineage, processing state and retry status. Reconcile all current consumers against new IDs before cutover. Copies are not additional independent creative candidates.
6. Source cleanup may only become automatic under an explicit bounded Critical Subset confirmation: media-only allowlisted staging paths, exact validated destination, no in-flight references, matching source identity/version, successful size/checksum and ownership verification, recorded lineage, working Service Account retrieval and agreed retention. Never empty a whole trash or delete unrelated files/folders/Sheets.
7. Source deletion must not occur in the initial copy pilot. Merely moving to trash does not promptly release quota. Any later permanent deletion is irreversible at the source and requires the additional approval; destination preservation and recovery checks are mandatory.
8. Replays must be idempotent and single-writer. Validate landed state before retry. Any missing verification blocks cleanup, preserves the source and creates an internal retry/exception record. Routine handling should be silent; only material decision/security blockers require Rodolfo.

## Acceptance and next gate

- Prove one isolated media copy, ownership/storage attribution, byte integrity and canonical Service Account readback.
- Test interruption/retry without duplicate archive candidates, concurrent processing protection and consumer/lineage parity.
- Validate Apps Script permissions, runtime/copy quotas and representative video sizes before assuming production capacity.
- Before activation, obtain the separate approval for the new account-authorized connector and bounded automatic permanent source-cleanup policy. Configure access to the real destination and obtain the account's initial Google consent through the protected login flow; never accept credentials/codes in chat.
- Only call the pipeline active after deployed runtime and end-to-end receipt verification. No user computer may be part of the steady-state execution path.
