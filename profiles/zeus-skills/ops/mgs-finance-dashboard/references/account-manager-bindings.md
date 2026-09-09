# Confirmed account/site/manager ownership

Canonical decision: `/root/mgs-agent/docs/finance-account-ownership.md`, source1547048317853114438 confirmed1547052028663169105. Resolve exact IDs and financial month there, then inspect live registry/workspace. Never use an old pending-account report as current state.

## Execution lessons
- Check whether site/account already exists before creating. Vizioid was inactive, not missing. Reuse its ID; activation affects current-month site allocation via existing engine rules.
- Separate site titular from account operator. Infinitynexx remains Joe; G001 account is Ícaro. Exact site+country is insufficient when source has principal/complementar blocks: bind segment too; honor explicit assignment before sticky prior target.
- G001 internal calculation identity is george, public label Ícaro. G002 is MGS/SEM_COMISSAO, not a new employee. Suffix parser accepts only terminal G001–G006 and preserves older monthly metadata.
- `accounts.mjs`: accountManager/manager_codes; per-month manager_bindings and auto_spend_binding including segment. `media-spend.mjs` retains manager metadata in native account_spend facts. Manual day editor must preserve it too.
- Native manager attribution must not double-debit costs already flowing through the audited source graph. `account_manager_costs.py` is explicitly enabled only by the site's native_account_managers flag (Yolokfx). Revenue is not divided from cost weights. Account-level costs appear in daily site and manager views; Accounts remains registry-only.
- Release helper `deploy/account-assignment-release.py` is a completed one-shot, not a generic rerun instruction. Keep exact before-state, dual backup/hash/restore, isolated rehearsal, compare unrelated scenarios/history/users/payment ledger, revision guards and readback. For another request make a new scoped plan rather than replaying this one-shot.
- Tests: `tests/account-manager-bindings.test.mjs`, `tests/test_account_manager_costs.py`, `tests/account-manager-public.mjs`; browser credentials from canonical1Password owner item passed only on stdin. Tests must assert real ID→site→manager→segment and source amount→daily UI, not just presence of account names.
- Broad Node suite at unbounded concurrency timed out with no failures; bounded `node --test --test-concurrency=2 tests/*.test.mjs` completed88/88 in~262s. Give foreground a600s budget; do not label a timed-out partial run green.

## Verified result
Private evidence `apps/finance-system/private/account-managers-1547052028663169105/`: nine existing accounts adjusted;63account/day records verified;14previously pending fields filled; idempotent repeat;4sites×2viewports;5manager API views;88Node+3Python PASS. Source APIs and Sheets were not written; no new access or credentials. Deployment restarted only finance app service, not any Hermes gateway. Earlier Mattei1/Infinitynexx pending statements explicitly superseded by this readback.
