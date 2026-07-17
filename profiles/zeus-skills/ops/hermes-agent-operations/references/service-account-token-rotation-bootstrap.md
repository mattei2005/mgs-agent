# Service-account token rotation and bootstrap

Use this playbook when rotating a 1Password service-account token used by Hermes/MGS runtime.

## Core invariant

A replacement token is not operational until the target host has read it and passed a real vault request. **Never revoke or delete the old service account before the new token is staged, validated, and installed.** Saving the new token inside a vault that is readable only through the old token creates a circular bootstrap dependency.

## Safe sequence

1. Identify the canonical runtime secret location and every process that reads it. For Zeus on MGS, the canonical file is `/root/mgs-agent/.env`, key `OP_SERVICE_ACCOUNT_TOKEN`, mode `0600`.
2. Create the replacement service account while authenticated as a human 1Password administrator. A CLI authenticated with `OP_SERVICE_ACCOUNT_TOKEN` cannot create another service account.
3. Grant only the required vault permissions. Preserve the previous scope unless Rodolfo explicitly authorizes a scope change.
4. Stage the new token without chat, command-line arguments, shell history, Git, logs, or rollback copies:
   - preferred: while the old token is still valid, store the replacement in an approved protected item and read it programmatically into memory; or
   - bootstrap fallback: have the human administrator edit the canonical `.env` directly with an interactive editor, replacing only the token value, then enforce mode `0600`.
5. Before changing runtime, validate the replacement with an actual network-backed operation such as reading one required vault item. `op whoami` alone is insufficient: it may decode local token identity even after the service account was deleted.
6. Replace the canonical secret atomically. Do not print token length, prefix, hash, or value unless a canonical procedure explicitly requires non-secret metadata; prefer only booleans such as `distinct_from_old=true` and check results.
7. Run post-cutover readbacks using the token loaded back from disk:
   - `op whoami` for identity metadata;
   - required 1Password item reads;
   - one real downstream consumer smoke test.
8. Only after every post-cutover check passes, revoke/delete the old service account.
9. Re-run the same vault reads after revocation to prove no process silently depended on the old token.
10. Record inventory/audit and REPORT-INFRA without credential material.

## Post-rotation operational closure

Credential readback is necessary but not sufficient when scheduled jobs depend on the token. After the new token passes vault reads:

1. Run one real downstream consumer for each distinct credential path rather than only `op whoami` or item metadata.
2. If disaster-recovery or other jobs were paused during containment, run a fresh encrypted backup and an isolated restore/readback with the new token before resuming schedules.
3. Restore only the previously approved cron/job definitions, preserve their original schedules, and validate exact readback rather than merely counting entries.
4. Update the incident state from `paused/pending` to active only after consumer, backup and restore evidence passes.
5. Re-scan active runtime code/config for the old identity or item while classifying audit/history separately.

Do not revoke first and plan to “read the replacement from the vault afterward.” A replacement stored in the same vault is not a bridge unless the host has already fetched and validated it.

## Emergency bootstrap after premature revocation

If the old service account was deleted before the replacement reached the host:

1. Stop retries with the dead token; a `403 Service Account Deleted` is definitive.
2. Check for a separately authorized human session or independent service account that can read the staged item. Do not assume sibling agents have separate credentials.
3. If no independent bootstrap identity exists, the human administrator must edit the canonical runtime secret directly on the host. Use an editor (`nano /root/mgs-agent/.env`) rather than a command containing the token, then `chmod 600 /root/mgs-agent/.env`.
4. The administrator must never paste the token into Discord. The agent validates only after the administrator reports that the file was changed.
5. If validation fails, keep the failure scoped to the credential bridge; do not recreate deleted OAuth or unrelated legacy credentials.

## Secret-containment pitfalls

- Do not include `.env` in rollback snapshots. Back up configuration structure separately from secret values.
- Do not put a token in `sed`, shell assignment arguments, process arguments, tool output, diffs, or reports.
- Do not treat permission sufficiency as proof a token is safe to retain. Rotation after exposure is about confidentiality, not capability.
- Do not delete a temporary protected item until the runtime readback and old-token revocation are complete.
- Do not call the rotation complete while either the old token remains active or the new token has not passed a real vault read.
