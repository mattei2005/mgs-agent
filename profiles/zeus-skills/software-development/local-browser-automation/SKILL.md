---
name: local-browser-automation
description: Build local Playwright/Node browser automations where the user logs in manually, then the script drives the browser to extract, download, or transform data from web apps without exposing credentials.
---

# Local Browser Automation

Use this skill when Rodolfo needs a local script that opens a real browser, lets him log in manually, and then automates a web app such as Messenger, Canva, Facebook, WordPress admin, or another authenticated UI.

## Core pattern

1. Prefer **manual login + persistent browser profile** over asking for credentials.
2. Use Playwright `launchPersistentContext(PROFILE_DIR, { headless: false })` so cookies/session persist across runs.
3. Start with a **small pilot** before building the full crawler/exporter.
4. Make the first pilot answer one technical question only: can the script see the useful DOM/data on the currently visible page?
5. After the pilot passes, add the expensive pieces incrementally: scrolling, dedupe, media download, OCR, CSV/XLSX export.
6. Keep outputs inspectable and resumable: `output/*.json` for raw data, `output/*.txt` for quick review, `output/images/` for downloaded media.

## Browser route discipline for Rodolfo

- When Rodolfo says **“seu navegador”**, **“browser do Zeus”**, or **“modo mobile”**, keep the operation in the Hermes-managed browser. Do not inspect or open AdsPower, PC1, Chrome Remote Desktop, or a user-owned desktop as a fallback unless he explicitly authorizes that route. A managed-browser failure authorizes diagnosis and failover inside the same browser class, not a silent environment switch.
- Configure mobile identity **before the first target navigation** and read it back: viewport, device scale, touch points, user agent/client hints, platform, locale/timezone, and `navigator.webdriver`. A mobile URL alone is not mobile mode, and a mobile user agent paired with a desktop platform or `webdriver=true` is an internally inconsistent fingerprint.
- Diagnose authentication from the application response, not from the visible generic toast. Capture only safe fields such as response code/message and selected risk decision/status values. Do not call a failure an IP or anti-bot block merely because it occurred on a VPS; a successful residential route does not prove authentication succeeded, and a normal risk decision/status rules out that causal claim.

## Rodolfo step-by-step mode

When Rodolfo asks for step-by-step execution, do **one step at a time**.

- Give the exact command block for the current step.
- Tell him the expected result.
- Wait for his result before sending the next step.
- Do not dump the whole plan again once he asks for commands.
- Keep explanations short; he is executing live in PowerShell.

Good format:

```text
Passo 2 — instalar dependências.
Roda:
```

```powershell
npm install playwright
npx playwright install chromium
```

```text
Resultado esperado: termina sem erro. Me manda “feito” ou o erro.
```

## Authenticated web app safety

- Do not request, display, or log passwords/tokens.
- Tell the user to log in manually in the opened browser.
- Persist profile locally so future runs do not require repeated login.
- Redact or avoid exporting unrelated personal data when present.
- If the user says data is fictitious/non-sensitive, you can simplify privacy warnings, but still avoid credential exposure.

## YouTube/short-form reference videos from VPS agents

When a user expects a creative agent to analyze a YouTube Shorts/Reels-style reference, do not assume “use Playwright/Chromium” is enough. On VPS/datacenter IPs, YouTube can load the page in Chromium but still withhold the stream with `LOGIN_REQUIRED` / “Sign in to confirm you’re not a bot”. The durable pattern is:

1. Build/use a persistent Chromium profile with `launchPersistentContext(...)` instead of a fresh browser each run.
2. Probe the player before producing creative work: check `video.currentSrc`, `readyState > 0`, `videoWidth/videoHeight > 0`, screenshot, and `ytInitialPlayerResponse.playabilityStatus`.
3. If the persistent profile is not yet trusted/logged in, report the blocker; do not create the final asset “inspired by” a reference the agent did not actually see.
4. Prefer low-cost fixes before paid browser/proxy products: one-time login/manual session, persistent cookies/profile, or user-provided video attachment. Residential Browserbase/proxy is a later option only if reference-link analysis becomes recurring enough to justify cost.
5. If cookies are needed, make them persistent for the profile; never ask for cookies per video and never paste cookie contents in chat.

## DOM extraction before screenshots/video

For large conversations or feeds, avoid screenshots and screen recording as the primary extraction method.

Preferred order:

```text
1. DOM extraction from visible elements
2. Scroll + collect + dedupe
3. Download image/media URLs found in DOM
4. OCR only on downloaded images that contain copy
5. Export JSON/CSV/XLSX
```

Use screenshots only for debugging or for media that cannot be downloaded from the DOM. Screen recordings are usually the worst source for text extraction because OCR over video loses order, creates duplicates, and is expensive to process.

## Messenger/conversation harvesting pattern

Messenger and similar apps virtualize long conversations: old messages unload as new ones enter the viewport. The script must collect incrementally while scrolling.

Recommended sequence:

1. Open browser to `https://www.messenger.com/`.
2. User logs in and opens the target conversation.
3. User returns to terminal and presses Enter.
4. Pilot collects currently visible candidates: `[role="row"]`, `[role="gridcell"]`, `div[dir="auto"]`, `span[dir="auto"]`, `a`, `img`, and relevant `aria-label` values.
5. Save `visible-messages.json` and `visible-messages.txt`.
6. If useful data appears, build full scroll collector:
   - collect visible elements;
   - scroll up/down by controlled increments;
   - wait for DOM stabilization;
   - dedupe by text, image URL, CTA/link, timestamp, and approximate position;
   - stop after top/bottom sentinel or repeated no-new-data cycles.
7. Export raw JSON first, then CSV/XLSX for analysis.

See `references/credentialed-dashboard-readonly-audit.md` for secure 1Password-backed, read-only vendor dashboard inspection: unattended login, menu/detail traversal, live-counter validation, executive interpretation, and credential-state cleanup. See `references/messenger-harvest-pilot.md` for the pilot workflow from the Messenger/ChatPion broadcast extraction session. See `references/messenger-chatpion-card-extraction.md` for the corrected message-block model: card image URL + card text + CTA/button + follow-up preview message. See `references/messenger-image-harvest-packaging.md` for image URL de-dupe, conservative image harvesting, and ZIP path normalization pitfalls. See `references/persistent-chromium-video-references.md` for VPS YouTube/Shorts reference analysis using a persistent Chromium profile, temporary localhost-only noVNC login, player-state validation, and frame capture fallback when `yt-dlp` cannot download the MP4. See `references/youtube-reference-vps-persistent-profile.md` for the VPS/YouTube reference-video pattern: persistent Chromium profile, player probing, and no-extra-cost fallbacks before paid residential proxy infrastructure. See `references/smartbidding-headed-xvfb-auth0.md` for the Smart Bidding/Auth0 route that worked: Playwright `headless=False` under Xvfb, persistent storage state, and 1Password `--reveal` credential parsing. See `references/meta-ads-library-persistent-collector.md` for the durable Meta Ads Library collector pattern, strict anti-false-positive smoke gates, control-query diagnosis, and one-time manual login into a persistent profile. See `references/persistent-authenticated-browser-runtime-hardening.md` for the class-level production checklist: exclusive profile locking, incremental extraction, strict media validation, safe diagnostics, sandbox/site-isolation posture, and repeated smoke gates. See `references/ssh-home-socks-auth-continuity.md` for localhost-only noVNC plus remote dynamic SSH SOCKS through the user's home connection, route-consistent authentication, safe stale-listener recovery, and CAPTCHA-loop handling. See `references/dedicated-residential-proxy-browser-runtime.md` for promoting a 1Password-backed dedicated residential proxy through a snapshot canary, fail-closed route enforcement, trusted-device preservation, and zero-touch authenticated operation. See `references/meta-business-settings-persistent-browser.md` for Meta Business Settings writes after manual passkey/2FA: exact-BM validation, forwarding URLs into an existing Playwright profile, screenshot-gated interaction, ad-account readback, and secure noVNC closeout.

## ChatPion/Messenger broadcast cards

When extracting Messenger broadcasts generated by ChatPion-like flows, treat the conversation as **message blocks**, not loose images or OCR jobs.

Common block types:

1. **Card block** — image/preview creative, title/body text rendered in the Messenger card, CTA button text, button/link URL, and often a follow-up text bubble immediately below so mobile notifications show useful preview copy instead of only “attachment”.
2. **Pure text block** — message text contains the hook, CTA phrase such as `👇 See your offer:`, and the offer URL directly; no image and no Messenger button.

For this class, “baixar os textos das imagens” usually means **download/extract the text fields rendered around the image card in the Messenger DOM**, not OCR the pixels inside the JPG. Do not spend time on Tesseract/OCR unless the user explicitly asks to read text embedded inside the creative image itself.

## Pitfalls

- Keep Chromium's `TMPDIR` short enough for Linux Unix-domain socket paths. Deep task-ID scratch subdirectories can trigger `FATAL ... Socket path too long` even when the same smoke passes with the profile scratch root. Retain evidence in the task directory but run browser temp/profile sockets under the short allowed profile scratch root; do not fall back to system `/tmp` or remove protected persistent browser profiles.
- For real-browser QA of a self-hosted panel with strict CSP, prefer Playwright locator assertions such as `expect(locator).to_have_text(...)` over `wait_for_function` with an expression string: the string path invokes `eval` and can fail under `script-src 'self'`. Fix the test harness, never weaken the application CSP to make a smoke pass. Keep QA dependencies in a project-owned isolated environment and reuse an existing compatible Chromium without changing protected agent runtimes or browser caches.

- For recurring agent browser automation, never leave the runnable collector, persistent profile, cookies, or required outputs under `/tmp`. Put code in a versioned project path, keep the browser profile in the owning Hermes profile's `browser-profiles/` directory with restrictive permissions, and keep generated runs in a durable profile-local artifacts directory. Session files must not be committed or printed. A filesystem-persistent session can still expire at the remote service; persistence prevents local deletion, not server-side expiration.
- When a VPS login succeeds only through a user-owned SSH SOCKS route, do not ask the user to close the tunnel immediately after login. Close the headed browser cleanly, then run the exact target smoke through the same route; only release the tunnel after authenticated readback succeeds. If the last success used that route, never probe `direct-vps` first with the same profile. If authentication indicators later disappear, report the observed sequence without inventing causality, then reauthenticate visually through the original route.
- For long-running browser collection in Discord, never enable automatic raw background completion output. Poll/wait manually and publish only a concise validated summary; keep full JSON/logs in the artifact directory.
- For virtualized ad/feed libraries, collect on every scroll and stop only after repeated no-new-data cycles or a safety ceiling. Report IDs, media URLs, and downloaded files separately; grouped ads and reused creatives make those counts differ.
- Do not assume copy/paste captures full history; virtualized chats often only copy loaded messages.
- Do not start with full automation. Validate visible DOM access first.
- Do not rely only on `innerText`; also inspect `aria-label`, `href`, `src`, and visible bounding boxes.
- For target-specific known Messenger URLs, navigate directly to `/t/<thread_id>` instead of asking the user to open it manually.
- Deduplicate aggressively. Scroll-based collection repeats DOM windows.
- For image-heavy broadcasts, DOM + image URL download + card/CTA DOM extraction is more scalable than screenshots. OCR is optional and secondary.
- Some authenticated dashboards distinguish headless from headed automation. If headless reaches login but the app rejects runtime validation, retry with a headed browser under Xvfb, persistent storage state, and a normal user-agent before concluding the dashboard is inaccessible.
- Keep the browser open until the user has verified output files exist.

## Minimal pilot structure

A pilot script should:

1. create `browser-profile/` and `output/`;
2. open Chromium non-headless;
3. navigate to the target app;
4. prompt the user to log in/open the target page;
5. wait for Enter;
6. evaluate visible DOM candidates;
7. filter by bounding box visibility;
8. save both JSON and TXT;
9. wait for Enter before closing.
