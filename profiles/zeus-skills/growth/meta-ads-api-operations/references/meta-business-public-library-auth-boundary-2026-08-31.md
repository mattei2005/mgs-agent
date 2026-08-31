# Meta Business auth boundary and Digital Trust validation — 2026-08-31

## Why this reference exists

A successful Ares Meta Ad Library download does not prove that the same persistent Chromium profile is authenticated for Meta Business Settings.

## Durable boundary

- The public Meta Ad Library can return ads and downloadable MP4s with HTTP 200 while the collector reports `authenticatedLikely=false`, exposes a login prompt, or lacks authenticated cookie-name markers.
- Therefore, “Ares downloaded videos today” is not evidence that `business.facebook.com` is logged in.
- When asked to reuse the Ares session, first identify the exact `profileDir` from the latest collector report, then navigate the requested Business Settings URL in that same profile via ProcessSingleton.
- Only the live Business page proves usable access: verify Business Portfolio name, exact `business_id`, `Ad accounts`, enabled `Add`, and the `Create a new ad account` form.
- If Business Settings redirects to login, reopen the canonical localhost-only noVNC wrapper and let Rodolfo complete login/passkey directly. Never request password or codes in chat.

## Validated Digital Trust flow

- Persistent profile: `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium`.
- Target: `Digital Trust`, `business_id=155263197283282`.
- Parameters: `name=001`, `timezone=America/Los_Angeles`, `currency=USD`, `usage=My business`.
- The final button entered a processing state for more than five seconds before `Ad account created successfully`; do not retry while the request is still visibly processing.
- Post-write readback:
  - real Ad Account ID: `2235938116947880`;
  - owner: `Digital Trust`;
  - assigned user: `Rodolfo Mattei`, Full access;
  - currency: `USD`;
  - timezone shown after creation: `Pacific Time`;
  - payment methods: none.
- The URL carried `selected_asset_id=52539984569350`, which was not the real Ad Account ID. Report the panel's `ID:` or `business_object_ui_id`, never `selected_asset_id`.
- After readback, close the browser and verify no profile process and no localhost VNC/noVNC listener remains, so Ares can reuse the profile.
