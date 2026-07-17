# Service Account identity replacement: permission closure

Use this after replacing a Google Cloud project, Service Account, or client email—even when the new identity uses the same local name.

## Durable pitfall

Google Drive permissions attach to the exact Service Account email/principal. Access granted to an identity in an old project does not transfer to a same-named identity in a new project. A healthy Shared Drive root therefore does not prove that individually shared My Drive Sheets are accessible.

## Closure sequence

1. Freeze the canonical project ID, client email, 1Password item, Shared Drive ID and expected auth selectors.
2. Build the operational file closure from active scripts, configs, jobs, skills and approved on-demand procedures. Keep historical/session-only IDs separate.
3. Probe every active file with the new identity on both surfaces:
   - Drive `files.get(...supportsAllDrives=true)`;
   - Sheets `spreadsheets.get` for spreadsheets.
4. For each existing My Drive Sheet returning Drive 404 or Sheets 403, share the same file with the new Service Account as Editor. Preserve its ID, Forms, formulas and `IMPORTRANGE` topology.
5. Reprobe and require Drive HTTP 200, Sheets HTTP 200, `canEdit=true` and `canModifyContent=true`.
6. Run one bounded write/readback/restore canary on a blank, unmerged and unprotected cell after permission rollout.
7. Validate the entire active closure again—not only the repaired files—and report counts by Shared Drive vs individually shared My Drive.
8. Remove old credential files, selectors and wrappers only after the new identity passes the complete closure.

## Residue scan

Scan more than production scripts. Include:

- root `.env` key names without values;
- root crontab, Hermes jobs and systemd units;
- live Zeus/Atena/Ares skills and their executable support scripts;
- linked operational references that could instruct the retired method;
- profile-local generic Workspace helpers;
- versioned mirrors and synchronization rules;
- root-only secret directories for credential-bearing primary/backup files;
- watchdog state files that still claim the old identity is primary.

Classify Git history, audit logs, imported Discord history and explicit archive/backup directories as read-only evidence. They may retain historical terms, but must not be executable, routed or presented as fallback.

## Fail-closed compatibility

If an obsolete script name must remain for callers or auditability, replace its implementation with an explicit nonzero tombstone that points to the canonical consumer. Validate the expected failure code. Do not leave a dormant wrapper that silently selects the retired mode.

For generic Workspace skills that cannot safely use the production Service Account for user-scoped services, keep Drive/Sheets on the canonical helper and block Gmail/Calendar/Contacts until a separate corporate identity is approved.

## Evidence to retain

- canonical project/client email readback;
- number of active files probed and passed;
- one reversible canary result;
- exact absence checks for retired credential paths;
- zero-hit active residue scan;
- scheduler/service zero-hit scan;
- live/versioned mirror parity;
- inventory, checkpoint, audit and infrastructure report IDs.
