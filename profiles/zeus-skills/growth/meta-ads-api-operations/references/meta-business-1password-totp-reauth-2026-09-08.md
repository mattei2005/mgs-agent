# Meta Business reauthentication with 1Password TOTP — 2026-09-08

## Scope

Validated recovery of a Meta Business Settings browser session for the approved Rodolfo Facebook identity while a scheduled Digital Trust ad-account batch was blocked by `/security/twofactor/reauth/`.

Credential reference only; no secret or generated OTP belongs in this file:

- 1Password vault: `MGS Conteúdo`
- Exact item title: `accountscenter.facebook.com`
- Required field type: `one-time password`

## Validated sequence

1. Preserve the exact persistent Chromium profile and acquire its exclusive collector/browser lock.
2. Start the headed session behind localhost-only noVNC. If the canonical login helper allowlists only Meta Ad Library URLs, start there and forward the exact Business Settings URL into the existing Chromium ProcessSingleton; do not weaken the helper allowlist.
3. Classify a page containing `Confirm it's you with your passkey` or `Try another way`, or a final URL under `/security/twofactor/reauth/`, as a reauthentication gate before any write.
4. Choose `Try another way` → `Authentication app`.
5. Resolve the 1Password item by exact title and vault. Fail closed on zero or multiple matches.
6. Retrieve one fresh code internally with `op item get <exact-item-id> --vault 'MGS Conteúdo' --otp`. Require exactly six digits. Fetch close to submission and, if the current 30-second window is nearly expired, wait for the next window before fetching.
7. Enter and submit the code without printing it, putting it in command output, logs, screenshots, files, audit payloads, Discord, or a shared clipboard.
8. Treat disappearance of the reauth gate as preliminary success, not final operational proof.
9. Close the headed session cleanly, release the profile lock, and run the canonical read-only Business preflight.
10. Require the expected Business ID/name, `preflight_ok`, `create_form=true`, no maximum-account gate, and `meta_writes=0` before clearing the batch blocker.
11. Resume only the already-authorized batch scope and cadence. Validate the first natural scheduler tick independently before calling the lane operational.

## Validated evidence

The code generated from the exact 1Password item was accepted by Meta. The subsequent read-only preflight reached the intended Digital Trust Business Settings page, found the account-creation form, found no visible maximum-account gate, and performed zero Meta writes. After blocker clearance, the first natural scheduled tick created and validated one additional account, advancing the batch from 27/40 to 28/40.

## Interpretation and safety boundaries

- A blank Business content pane immediately after successful TOTP submission can be a render condition. Do not classify authentication as failed from the blank pane alone; use the canonical preflight.
- TOTP works only when Meta offers `Authentication app`. It does not bypass an exclusive passkey, trusted-device approval, checkpoint, unusual-activity review, or other security gate.
- Never store the generated OTP. Store only the 1Password item reference and sanitized validation result.
- Adding, replacing, or rotating the TOTP secret is a credential change and follows the Critical Subset confirmation rule. Reading an already approved TOTP for an authorized recovery is not a credential mutation.
- Clearing a blocked batch is allowed only after the post-auth preflight and only within the unchanged target, defaults, payment scope, identity and cadence already authorized.
