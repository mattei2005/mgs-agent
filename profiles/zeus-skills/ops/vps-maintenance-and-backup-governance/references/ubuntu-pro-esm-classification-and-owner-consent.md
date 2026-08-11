# Ubuntu Pro / ESM classification and owner consent

Use this reference when a VPS audit reports security updates available only through Ubuntu Pro or ESM Apps.

## Classification before recommendation

1. Read the live client state with `pro status` and `pro security-status --format json` (or the supported machine-readable `pro api` equivalent).
2. Report these classes separately:
   - standard Ubuntu security updates currently available;
   - ESM Infra updates;
   - ESM Apps updates;
   - whether the machine is attached;
   - standard-support end date and whether reboot is required.
3. Never describe ESM Apps as a blocker for an otherwise current Ubuntu installation. If standard updates are zero and the running kernel/services are healthy, say the base system is current and ESM Apps is optional expanded coverage.
4. `num_esm_apps_updates` counts package update entries, not distinct CVEs or distinct vulnerabilities. Group related binary packages into software families before explaining impact (for example FFmpeg libraries, ImageMagick libraries, pip/wheel).
5. Explain practical exposure rather than listing package names alone: media parsers matter when untrusted images/audio/video are processed; package tooling matters during dependency installation; libraries installed only transitively may have lower immediate exposure.

## Device-code flow

- Before starting `pro attach` in a general maintenance flow, state plainly that it links the machine to an Ubuntu Pro subscription/account and is optional expanded security coverage.
- If the owner explicitly requests a new device code, generate it directly, but include that one-sentence context so the code is not mistaken for an ordinary Ubuntu update step.
- Keep the waiting process bounded and manually supervised. If the owner declines or questions the need, stop/let the device code expire and verify `attached=false`; do not leave a waiting process or imply any subscription was created.
- Do not claim free/commercial eligibility from memory. Check Canonical's current official terms when price or licensing matters.

## Supervised attachment and local readback

1. Run `pro attach` in a tracked PTY process. In Discord operations, keep it silent from automatic completion notifications and supervise it with manual `poll`/`wait` calls.
2. Poll only until the device URL and temporary code appear, then send those values to the owner. Keep the PTY alive; terminating it after extracting the code invalidates the pending flow.
3. After the owner confirms the browser step, wait until the local process exits. Browser confirmation is not proof that the host attached successfully.
4. Require a fresh `pro status --format json` readback with `attached=true` and inspect the actual states of `esm-apps`, `esm-infra`, and `livepatch`.
5. For Livepatch, confirm the running kernel is supported and report its patch state. `enabled` proves entitlement/configuration, not that a patch was applied; `nothing-to-apply` is a valid healthy result.
6. Never publish subscription identity, client secrets, tokens, or private Ubuntu Pro state. Inventory/report only the subscription class and validated service states.

## Separate attachment from package installation

Attachment and ESM package installation are two distinct state changes and authorization gates:

1. After attachment, freeze the package set with `apt list --upgradable`, `apt-get -s upgrade`, and `pro security-status`.
2. State explicitly when attachment succeeded but ESM packages remain pending.
3. Under MGS policy, obtain the Critical Subset confirmation before installing the frozen set because the upgrade writes under `/usr`, even when the owner has just completed device attachment or previously requested broad VPS maintenance.
4. Do not enable unrelated Pro services such as FIPS, realtime kernel, Landscape, or USG unless separately requested.
5. After confirmation, follow `controlled-package-and-node-tooling-update.md` for exact candidate versions, rollback evidence, narrow installation, and service/reboot closure.
6. Post-install acceptance requires: zero intended updates remaining, clean `dpkg --audit`, current/expected kernel agreement, reboot-marker and `needrestart` readback, zero failed units, target gateways active, and no new critical logs. A required reboot is a separate gate governed by the durable post-reboot validator.
7. Record validated attachment/config changes in inventory and audit, then publish the canonical REPORT-INFRA embed without account identity or token material.

## Executive wording

Use this order:

1. Base Ubuntu state: current or not.
2. ESM state: optional expanded coverage and package-family count.
3. Practical risk: what installed families protect and whether they are exposed.
4. Decision: activate now, defer, or ignore, with no implication that healthy base maintenance is incomplete when only ESM Apps remains.
