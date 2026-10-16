# Codex authentication recovery and interrupted-thread delivery

Use when a gateway posts a generic model-service connection error or authentication failure and Rodolfo requests recovery. The screenshot identifies the symptom; the exact thread and gateway logs identify the failure stage.

## Procedure

1. Read the target thread and identify the original human request, failed replies, executor, and existing completion evidence. Correlate the exact thread/session with gateway logs. A `Model resolution failed` entry before agent execution explains an unprocessed input; do not infer the state of older campaign writes from it.
2. Apply the incident and identity gates in `references/providers-codex-oauth.md` before proposing credential changes. Check current provider incident timestamps, not merely an older extracted status page. An ended-session refresh error proves rejection of that refresh attempt, not why the session ended.
3. Inspect the profile's auth store without disclosing secrets. Resolve `credential_pool.openai-codex[]` as well as any legacy provider block; report pool count, source, refresh time, and token-presence booleans only. Token-shaped fields do not prove validity.
4. If Rodolfo says he already logged in, reread the affected stores and go directly to the smoke test before initiating another login. When several profiles were authenticated, test them after the last login, preferably concurrently; testing each before the next login does not demonstrate simultaneous usability.
5. If the affected profile still fails and a login is needed, obtain the credential Critical Subset confirmation. Back up auth outside Git in a protected directory, preserve config/model/billing, and use the supported profile-scoped OAuth flow. `hermes -p <profile> auth add openai-codex --type oauth` adds a pooled credential; it does not replace or validate every older entry. Do not remove old entries or copy another profile's credentials as part of an unapproved cleanup. A same-account warning alone does not prove cross-profile revocation or require new subscriptions; apply the evidence gate in the provider reference.
6. Run the bounded connectivity check below using each profile's own configured provider/model. Keep logs local and report only profile, process exit status, exact-marker match, and sanitized failure classification. Do not expose device codes, auth responses, tokens, or raw provider traces.
7. Check gateway `active/running` separately. Authentication-only recovery does not inherently require restart; restart only if live evidence shows the gateway still cannot use the recovered access, and then use the canonical detached safe-restart workflow. CLI success does not prove that a Discord turn has run.
8. Update the original thread with the verified access state and remaining business-task state, then read back the exact posted message. Use Zeus authorship for diagnosis; never impersonate the executor or present a generated answer as completed production work.
9. Recover the original business request through its authorized executor, with one owner and readback of prior side effects before any non-idempotent retry. Preserve account, IDs, budget, strategy, quantities, and start time. Follow `discord-ops` for authorized handoff and verify fresh executor activity; posting a status update is not a resumed execution. If handoff authority or a production gate is missing, state that exact blocker rather than manufacturing a completed delivery.
10. Close three gates independently: **model access validated**, **gateway/Discord execution observed**, **original deliverable verified**. Record audit/checkpoint/report evidence when operational state is changed, without credential material.

## Bounded exact-marker connectivity check

Check `hermes chat --help` in the deployed runtime before reusing flags. The following form exercises the profile's configured model without loading business history or requesting tools:

```bash
/root/.local/bin/hermes -p <profile> chat -Q --oneshot \
  --ignore-rules -t '' --max-turns 1 --run-budget 75 \
  --reasoning minimal \
  -q 'Teste inofensivo de conectividade. Não use ferramentas, não grave memórias nem skills. Responda somente: MGS_AUTH_OK_<PROFILE>'
```

Run from scratch through a foreground subprocess with an outer timeout, capture stdout/stderr privately, and require both exit code zero and the marker as an exact output line. Do not accept a marker merely echoed inside a prompt or error. For several profiles, a bounded `ThreadPoolExecutor` can run one subprocess per profile; aggregate every requested profile before reporting the result. A timeout or nonzero exit is not a pass even if text was printed.

`--ignore-rules` keeps this probe separate from normal operational instruction loading; it is not a workflow for bypassing rules on production requests. The probe may create ordinary CLI session/runtime records and refresh OAuth normally; do not describe it as a filesystem-no-write test or as a long-term token-renewal guarantee.

## Interpretation and reporting

- When all post-login probes pass, say that model access works now and preserve the working setup. Do not demand another authentication round solely because the CLI warned about the same account.
- Explain that repeated credentials for the same account do not add quota. Keep duplicate-pool hygiene separate from immediate recovery because removing credentials changes auth state.
- Describe copied rotating refresh tokens as a specific risk only when copying is actually evidenced. Different tokens and successful simultaneous calls do not establish future refresh-family independence.
- Report the affected profile's proven failure without claiming the other profiles were broken merely because Rodolfo renewed all of them.
- Keep the executive answer short: proven cause, tested profiles, significance of the warning, and exact remaining delivery gate. Avoid saying the campaigns/report are complete when only inference was validated.
