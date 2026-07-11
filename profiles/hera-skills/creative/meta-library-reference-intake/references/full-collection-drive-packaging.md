# Full Meta Library collection → sanitized Drive package

Use when the request is to download **all available creatives** from one Ads Library search and organize them in Drive as references.

## Completion pipeline

1. Preserve the authenticated browser profile and its network route. If the session was established through `windows-home-socks`, use that route for the helper and collector; never probe `direct-vps` first.
2. When login/2FA or “trust this device” was used, close Chromium cleanly, release the profile lock, and require a secure profile snapshot before collection. Do not touch the profile again after the collection if a snapshot-preservation instruction is active.
3. Run the full collector with:
   ```bash
   HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080 \
   hera-meta-library-collector.sh --url '<URL>' \
   --scrolls 100 --download 100 --wait-ms 1800
   ```
4. Validate the report and every download: result count, distinct Library IDs, screenshot, HTTP 200, allowed MIME, matching magic bytes, byte count, and recomputed SHA-256.
5. Deduplicate by downloaded-file SHA-256, not filename or CDN URL. Preserve a duplicate map in the inventory. Report both raw download count and unique creative count.
6. Treat the material as reference-only. Sanitize each unique file and require `clean=true` plus `harmful_tags_after=0` before Drive upload.
7. Package only sanitized unique creatives with:
   - `README.txt` — source, counts, sanitization status, reference-only notice;
   - `inventory.json` — source report, raw/unique counts, duplicate map, dimensions, MIME, hashes, cleaning status, Drive IDs/links;
   - a clean reference folder using human-readable sequential names such as `FMYBC_LIBRARY_REF_IMG_01.jpg` and `FMYBC_LIBRARY_REF_VID_01.mp4`.
8. Upload into a dedicated reference folder under the approved Drive root. Do not place third-party Library material in campaign `READY` folders.
9. Upload the finalized inventory after creative Drive IDs/links are populated.
10. Perform independent readback: expected child count, exact parent, `trashed=false`, non-zero size, and Drive MD5 matching every local sanitized file. Verify README and inventory separately.

## Drive OAuth precedence pitfall

When the Drive watchdog says the complete OAuth client cache is `token_ok` but the upload client returns HTTP 400, inspect credential precedence without exposing values. The established client may read the healthy client cache and then override its refresh token from an older token-only file. During a live task, do not delete canonical credentials: bypass only the stale token-only override with an isolated nonexistent root-only path, keep the watchdog-validated client cache, mint the access token, and validate root metadata. Record the canonical precedence remediation separately through REPORT-INFRA.

## Reporting

Return a compact aligned summary containing:

- displayed result estimate and Library IDs;
- raw downloads, duplicates removed, unique image/video counts;
- sanitizer totals;
- Drive folder link;
- uploaded/read-back child counts;
- explicit reference-only status.

Never expose cookie values, cookie hashes, OAuth values, CDN query strings, or raw background-process output.