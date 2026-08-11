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

## Executive wording

Use this order:

1. Base Ubuntu state: current or not.
2. ESM state: optional expanded coverage and package-family count.
3. Practical risk: what installed families protect and whether they are exposed.
4. Decision: activate now, defer, or ignore, with no implication that healthy base maintenance is incomplete when only ESM Apps remains.
