# MGS agent Codex auth repair + answering the blocked Discord thread

Use when an MGS agent (Ares/Atena/agente legado/Zeus) posts `Provider authentication failed` in Discord and gateway logs show Codex/OpenAI-Codex refresh failure such as `Invalid refresh token` or `refresh_token_reused`, and Rodolfo asks Zeus to fix it and make the agent answer the original thread.

## Operational pattern

1. Confirm the failing profile and thread from the screenshot/logs.
2. Inspect the affected gateway logs for provider auth errors without printing tokens.
3. Inspect profile auth state in sanitized form only: active provider, provider names, token length/presence, `last_refresh`, `last_auth_error`. Never print access/refresh tokens.
4. Prefer an independent OAuth device-code login for the affected profile. This is the durable repair.
   - Backup the affected `auth.json` outside Git first, e.g. `/root/.hermes/secure-backups/<agent>/auth.json.pre-codex-fix-<ts>` with mode 600.
   - Do not create auth backups under `/root/mgs-agent` or any versioned path.
   - Copying a currently working `openai-codex` provider block from another profile is emergency-only and requires critical confirmation. It restores immediate access but clones a rotating single-use refresh token; schedule independent re-auth before expiry and never report the copy as a durable fix.
5. Validate the profile with a real smoke call, e.g. `/root/.local/bin/hermes -p <agent> -z 'Responda apenas: OK_<AGENT>'`.
6. Generate the answer through the repaired profile when possible, not as Zeus impersonation. For Ares: use `hermes -p ares -z '<self-contained prompt>'`.
7. Post the generated answer into the original Discord thread via the agent’s own Discord poster when available, e.g. `/root/mgs-agent/scripts/ares-discord-post-with-thread.py --thread-id <thread_id>`.
8. Verify by Discord readback that the agent’s message exists in the target thread.
9. Restart the affected gateway only after the auth fix if the live gateway had already failed inside the conversation state; validate `systemctl is-active` and another smoke call after restart.
10. Append audit log entries with paths and validation, but never token material.

## Pitfalls

- `active` systemd service does not mean model auth works. Run a direct `/root/.local/bin/hermes -p <agent> -z ...` smoke test.
- A copied OAuth block can pass immediately and still fail later when cloned profiles race the same single-use refresh token. Compare token identity internally without printing it and require independent re-auth for durable closure.
- `auth.json` may contain token-shaped fields even when the refresh token is invalid. Trust real smoke output and `last_auth_error`, not mere token presence.
- Do not answer only as Zeus when Rodolfo explicitly asks to make the affected agent answer a thread. Repair the affected profile, generate/post as that agent, then verify readback.
- After copying auth, restart may log the old process SIGTERM as `exit-code`; classify by the new service state, MainPID, recent logs, and smoke test.
