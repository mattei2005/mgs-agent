# Full Meta Library collection → sanitized Drive package

Use when the request is to download **all available creatives** from one Ads Library search and organize them in Drive as references.

## Completion pipeline

1. Preserve the authenticated browser profile and use the default `dedicated-us-residential` route resolved by the wrapper. Do not set `ARES_META_LIBRARY_PROXY` during normal operation; `windows-home-socks` is fallback only after reporting dedicated-route failure, and `direct-vps` is prohibited.
2. When login/2FA or “trust this device” was used, close Chromium cleanly, release the profile lock, and require a secure profile snapshot before collection. Do not touch the profile again after the collection if a snapshot-preservation instruction is active.
3. Run the full collector with:
   ```bash
   ares-meta-library-collector.sh --url '<URL>' \
   --scrolls 100 --download 100 --wait-ms 1800
   ```
4. Validate the report and every download: result count, distinct Library IDs, screenshot, HTTP 200, allowed MIME, matching magic bytes, byte count, and recomputed SHA-256.
   - **Mandatory maximum-quality gate — videos:** never assume `video.currentSrc` is the best source; Meta may expose only an SD preview there. Inspect the player DOM and React props/fiber for `hdSrc` or equivalent higher-quality sources, download candidates through the same authenticated browser context, and compare actual ffprobe dimensions/bitrate. Select the highest valid HTTP 200 MP4 with matching magic bytes and full decode. Record explicitly when only SD is exposed.
   - **Mandatory maximum-quality gate — images:** do not select a thumbnail or the first `img.currentSrc` blindly. Inspect `srcset`, DOM/React props and accepted CDN candidates, download the available variants through the same browser context, validate HTTP 200 plus image magic bytes, and select the candidate with the largest real pixel dimensions; use bytes/visual integrity as tie-breakers. Record explicitly when only a low-resolution source is exposed.
   - Apply these quality gates before deduplication, sanitization, naming, Drive upload or any claim of “best quality.” Never upscale or transcode a low-quality source merely to label it HD.
   - Known collector pitfall: when `mediaLinkedToCardCount > 0` but is much smaller than `imageCount + videoCount`, the current candidate-selection branch may download only the linked subset and silently omit virtualized videos. Do not package that partial run. Use a task-local copy of `collector.js` under the Ares artifact directory, preserve the canonical profile/lock/proxy rules, change only `fallbackCandidates` to all observed accepted media, rerun, and deduplicate by SHA-256. Do not patch the canonical production collector during a creative task; report the runtime defect through REPORT-INFRA for a separately authorized fix.
   - If videos download with `libraryId=null` while real IDs and media are present, the DOM card association may exceed the canonical `nearestLibraryId` ancestor depth. Use a task-local collector copy under the artifact directory, keep the same exclusive profile lock and residential proxy resolver, increase only the ancestor search depth (validated at 40), and rerun. Require `mediaLinkedToCardCount > 0` and a non-null Library ID on the selected download before reporting. Do not change the canonical collector during the creative task.
5. Deduplicate by downloaded-file SHA-256, not filename or CDN URL. Preserve a duplicate map in the inventory. Report both raw download count and unique creative count.
6. Treat the material as reference-only. Sanitize each unique file and require `clean=true` plus `harmful_tags_after=0` before Drive upload.
7. Package only sanitized unique creatives with:
   - `README.txt` — source, raw/unique counts, sanitization status, and reference-only notice;
   - `inventory.json` — source report, exact observed Library IDs, raw/unique counts, duplicate map, per-asset `library_ids[]`, dimensions/duration, MIME, source and clean hashes, cleaning status, and Drive IDs/links/readback fields;
   - mixed-media folders `IMAGES/` and `VIDEOS/`, with human-readable sequential names such as `FMYBC_LIBRARY_REF_IMG_01.jpg` and `FMYBC_LIBRARY_REF_VID_01.mp4`.
8. Resolve the current registered LIBRARY META below MGS-ARQUIVO/CRIATIVOS in the 30 TB archive. The former MGS-AGENTS/CRIATIVOS/LIBRARY META path is historical, not a staging root to recreate. Preflight the existing canonical SA/isolated-owner packaging route before promising uploads; do not upload SA binaries directly into My Drive or widen the owner lane if this reference-package class is unsupported. Preserve the same package and sanitized-file manifest, keep IMAGES/VIDEOS below the package and README/inventory at its root, and never put reference-only media in campaign READY.
9. Upload sanitized media first and perform per-file readback. Populate all creative Drive IDs, links, parent IDs, sizes, and MD5 results locally; upload `README.txt`; upload `inventory.json` last. If the inventory records its own Drive ID/link, patch it once and revalidate the final remote bytes.
10. Perform an independent readback after upload: exact parent chain, expected root/subfolder child counts, `trashed=false`, non-zero size, local bytes equal remote bytes, and Drive MD5 matching every sanitized file. Download `README.txt` and `inventory.json` with HTTP 200 and require byte-for-byte equality with the finalized local copies before reporting success.

## Retired personal-Google-OAuth workaround

The former personal client-cache/token-only refresh workaround is retired. Agents use only the canonical Service Account helper; the approved isolated owner connector is not an agent-auth fallback. Retain downloaded media and exact state on failure, diagnose the actual canonical boundary and resume only verified missing steps. Never restore personal Google tokens, bypass credential precedence, alter credentials/ACL or replay a landed package without its required authority/readback.

## Reporting

Return a compact aligned summary containing:

- displayed result estimate and Library IDs;
- raw downloads, duplicates removed, unique image/video counts;
- sanitizer totals;
- Drive folder link;
- uploaded/read-back child counts;
- explicit reference-only status.

Never expose cookie values, cookie hashes, OAuth values, CDN query strings, or raw background-process output.