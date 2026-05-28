# Canva Teams / Browser Automation Notes

Context: Rodolfo may have Canva Teams/Equipe rather than Enterprise and needs to move mixed Canva creative folders into the Drive asset library.

## Durable findings

- Canva Connect private integrations are documented as available only for Canva Enterprise teams. Canva Teams/Equipe should not be assumed to support private internal Connect API access.
- Public integrations are not the right default for internal MGS asset migration because they are intended for external/public distribution and can require Canva review.
- Google Service Account emails are useful for Google Drive API access, but they are not a practical Canva user login and should not be invited as the Canva folder user.
- For Canva UI access without Enterprise API, use a real operational email/user, not Rodolfo's personal/admin account. The email must be able to receive and accept the Canva invitation.
- Canva login codes / magic links are credentials. Never ask Rodolfo to paste them in chat. If operational email access is needed, use vault/1Password internally and only report non-secret status.
- Server-side/headless browser access to Canva may be blocked by Canva/Cloudflare before the login form. Treat this as a known risk of the UI-automation path, not as a password problem.

## Recommended path when Canva folders contain mixed image/video designs

1. Prefer official Canva Connect API only if Enterprise/private integration is available.
2. If using Canva Teams without private API, create a dedicated real Canva user such as `assets@...` or `criativos@...` and share one pilot manager folder with it.
3. Try a small pilot before bulk work: identify static designs vs video/animated designs, export static as PNG/JPG and animated/video as MP4, then upload/copy to Drive.
4. If server-side UI automation is blocked, move automation to Rodolfo's local computer/browser session where Canva is already logged in, or fall back to manual export plus Drive-side organization.
5. Keep originals immutable: do not delete/move the Canva or raw Drive source during the first pass; copy organized outputs and generate an inventory.

## Classification reminders

- Do not bulk download mixed Canva designs with one selected format: static images exported as MP4 and videos exported as PNG/JPG produce wrong operational assets.
- Separate first by media type: `IMG` vs `VID`.
- Then classify by placement using dimensions/aspect ratio: square/feed, 4:5 feed, 9:16 story/reels.
- Then classify language by filename/folder when reliable, otherwise OCR/visual review; uncertain assets go to `REVIEW`.
