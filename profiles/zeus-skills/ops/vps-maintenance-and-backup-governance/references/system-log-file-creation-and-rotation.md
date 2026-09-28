# System log file creation and rotation integrity

Use this when rsyslog or another daemon reports that a configured destination log is absent, unwritable, suspended, or repeatedly recreated with the wrong ownership or mode.

## 1. Freeze state before proposing a repair

Capture in one read-only snapshot:

- target existence, type, inode, owner/group, mode, size, mtime and ctime;
- parent traversal with `namei -l`, parent `stat`, `getfacl -cp`, default ACL and `lsattr -d`;
- daemon unit state, sandboxing/user settings, validated configuration and current-boot journal;
- the exact producer rule that names the log;
- every tmpfiles and logrotate rule that names the target;
- process FDs referencing the target or a deleted predecessor;
- package ownership of the relevant config files.

Reconcile concurrent changes through the audit log, inventory/control plane, Git and session history before calling them anomalous. Directory ctime proves change, not authorship.

If any existence, ACL, mode or config-hash precondition changes after authorization, stop before mutation. Record the attempt as a no-op and freeze a new manifest; never reinterpret a stale approval.

## 2. Attribute creation and rotation separately

Treat these mechanisms as different lifecycle stages:

- An rsyslog selector such as `mail.* -/var/log/mail.log` names a destination but may not have permission to create it.
- A tmpfiles `z` rule changes owner/mode of an **existing** path; it does not create an absent file. Creation requires a creating type such as `f`/`f+`, subject to the package's actual rule and semantics.
- Logrotate `missingok` only suppresses an error when the path is absent. It does not create the file.
- Logrotate `create MODE OWNER GROUP` recreates the destination after rotation. Without it, a manual one-time file creation can regress on the next rotation.

Validate rsyslog syntax with `rsyslogd -N1`. Validate the candidate logrotate stanza with `logrotate --debug` and an isolated state path; do not force a live rotation merely to test syntax.

## 3. Choose the narrow durable repair

When the configured target is absent and the parent directory is intentionally protected:

1. preserve the parent mode and ACL exactly;
2. create only the named target with the producer's required ownership and mode, for example:
   `install -o <owner> -g <group> -m <mode> /dev/null <absolute-log-path>`;
3. add or correct `create <mode> <owner> <group>` in the exact logrotate stanza that owns the path;
4. back up and hash the current rotation file, hash the candidate, and bind the authorization to both hashes and the exact target path.

Do not grant a service broad write access to `/var/log` merely to create one known file. An ACL mask can silently reduce the effective rights of a named entry, and a control-panel or hardening job can later reconcile the directory again. Exact-file provisioning plus rotation ownership is narrower and more durable.

If the target already exists and contains data, do not recreate or truncate it. Preserve contents and inode unless the approved repair explicitly requires otherwise; change only the minimum owner/mode/config fields.

## 4. Apply and validate

After exact confirmation:

1. re-read every frozen precondition;
2. save the config backup and its hash outside the target path;
3. validate the candidate, replace the config atomically, and create/correct the target;
4. rerun `rsyslogd -N1` and the isolated logrotate debug check;
5. record target size, send a unique non-secret `logger -p <facility>.<level> -- <marker>` probe, and wait only for a bounded retry window;
6. require target growth, exact marker presence, expected owner/group/mode, daemon `active`, and no new permission-denied/action-suspended journal entries since the mutation boundary;
7. prove the parent directory mode and ACL are byte-for-byte unchanged;
8. rerun the host's normal package, failed-unit, `needrestart`, application and public smoke gates.

Do not restart the daemon by default when a bounded producer retry can prove recovery. If the action remains suspended after the exact target exists and the configured retry window expires, stop and open a separate service-restart gate; never compensate by widening directory permissions.

## 5. Rollback and reporting

Restore the exact backed-up rotation config and revalidate syntax. Do **not** delete or truncate the newly active log as routine rollback—logs are operational data. If the owner explicitly authorizes removal of an empty test-only target, bind that deletion separately.

Treat a rollback that restores configuration but intentionally preserves the newly created log as an authorized partial state, not as the original pre-state. Before retrying, require the restored config hash, unchanged parent ACL, exact target owner/mode, and a unique marker or receipt tying the file to the approved attempt. Make the continuation idempotent: skip `install ... /dev/null` when that attributed file already exists, because repeating file creation would truncate operational evidence; resume only the unapplied config step and rerun the complete validation set.

Always return and persist a structured failure receipt containing the mutation boundary, surviving side effects, rollback fields, backup path, and target hashes even when the remote process exits nonzero. The caller must save that receipt before raising so the next attempt never reconstructs partial state from inference.

Report these states separately:

- reboot or package transaction completed;
- current logging health failed or recovered;
- defect attributed as pre-existing or maintenance-caused;
- production mutation applied or blocked as a no-op;
- restart avoided, required, or separately pending.

A defect can be pre-existing and still block a green current-health result. Preserve both facts instead of smoothing one into the other.
