# Canva local automation fallback for creative exports

Use this when Canva Connect API is unavailable/limited (for example Teams plan without private integrations) and server-side/browser automation is blocked by Canva/Cloudflare.

## Durable lesson

Do **not** assume Hermes `MEDIA:/path` will appear as a downloadable attachment in Discord for arbitrary local files. If the user cannot see the attachment, provide a manual file scaffold or an alternate transfer path.

## Recommended flow

1. Avoid using Rodolfo's personal Canva account for automation when possible.
2. Prefer a dedicated real Canva user/email for assets operations, with credentials in 1Password/vault and no secrets in chat.
3. If Canva blocks automation from the VPS, switch to **local automation on Rodolfo's computer**:
   - user logs in manually in the local browser;
   - codes/MFA are typed by the user locally;
   - session is stored in a local browser profile directory;
   - first run is **audit only**: screenshot + visible text + clickable element inventory;
   - only after reviewing the audit should a download script be tailored.
4. For Discord delivery failures, send files as text blocks by path/content:
   - `package.json`
   - `scripts/login-check.js`
   - `scripts/folder-audit.js`
   - `README.md`
   Split into numbered parts if a file exceeds Discord limits.

## Local package shape

```text
canva-local-automation/
├── package.json
├── README.md
└── scripts/
    ├── login-check.js
    └── folder-audit.js
```

## Security rules

- Never ask Rodolfo to paste Canva password, OTP, email code, or magic link into Discord.
- MFA/email-code entry happens only in the local browser by the user.
- The local script should not download/move/delete on the first pass; audit only.
- Session state belongs in `canva-profile/` and can be revoked by deleting that folder or revoking sessions in Canva.

## Follow-up after audit

Ask the user to send back:

```text
*-audit.json
*-audit.png
```

Then adapt the next script version to the actual Canva DOM/buttons to:

```text
IMG/static designs -> PNG/JPG
VID/animated designs -> MP4
unknown/ambiguous -> REVIEW
```
