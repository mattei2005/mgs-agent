---
name: openai-product-pilots
description: Use when piloting OpenAI Security or external plugins.
version: 1.0.0
author: Zeus — MGS
license: MIT
metadata:
  hermes:
    tags: [openai, codex, security, plugins, pilots]
    related_skills: [hermes-agent-operations, software-development-methods]
---

# OpenAI product pilots — MGS

## When to Use

Use for approved report-only Codex Security experiments and external ChatGPT/Codex plugin feasibility. Consult current official docs and installed command help; do not guess fields or flags.

## Security

1. Distinguish Security Cloud, plugin and official `@openai/codex-security` CLI. A browser challenge is an access-path blocker, not proof of outage or missing entitlement. Preparing a documented alternative path does not authorize silent reduction of code scope.
2. Inspect version, `info --json`, `scan --help` and `login status` with dedicated CODEX_HOME under the active Hermes profile. Pin package versions. Never copy raw Hermes OAuth tokens to authenticate another client. In CLI0.1.31, file-backed login lives at `$CODEX_HOME/state/plugins/codex-security/codex-home/auth.json`, not directly at `$CODEX_HOME/auth.json`; use login status plus path/permissions-only inspection, never credential contents.
3. Use an environment allowlist without 1Password, SSH, cloud or API keys. Explicit `--auth chatgpt` prevents headless auto-auth from choosing a billable key. Require user-mediated login and verified access; package availability does not establish entitlement. Trusted Access for Cyber may be required. Before a long scan, record the account-usage baseline and inspect quota during execution: included usage can still compete with production agents. If the residual allowance threatens continuity, cancel the scanner gracefully, verify exit and preserve partial artifacts. Redeeming banked resets, buying extra usage or switching to API requires Rodolfo's explicit decision; do not attribute all shared-account usage to the scanner without a baseline.
   - After explicit approval to consume exactly one banked reset, use the installed Hermes native redemption helper under the intended HERMES_HOME; never copy OAuth tokens. Read the helper's current signature/guards first. At less than100% usage, force redemption only when Rodolfo's approval already covers the observed non-exhausted allowance; the client guard and backend result are separate. Read back live usage and banked credits to prove one credit was spent before restarting a scanner. On an uncertain response, reconcile those values before any retry: a fresh redemption call may spend another credit. Reset one does not authorize reset two or paid API.
4. Keep outputs private and outside the repository. `--dry-run` validates local inputs only: no credential loading, access verification, code analysis or security findings. Label it preflight.
5. Report-only is not filesystem isolation. Official scans use local permissions, approvalPolicy=never and a fixed filesystem profile; --codex cannot restrict these controls. Require separately validated OS-level sandbox/source snapshot, no production secrets and isolated artifact writes before scanning. Never scan the operational worktree directly as root.
6. No --mock as evidence, --patch, --create-pr, Git hooks or production calls for a read-only pilot. Review findings, validation evidence and coverage complete/partial/unknown. No report means no completed scan. Do not send raw scanner logs to Discord.
7. Credentials, GitHub grants, billing and permission changes remain subject to MGS confirmation gates. State the exact blocker and scope; never claim dry-run substitutes for the authorized pilot.

## Security execution pitfalls and validated containment

- Build the approved source-only snapshot from one recorded Git revision. Keep an external file/hash manifest and report conservative credential-like exclusions as exclusions, not proven leaked secrets. Preserve failed snapshot attempts privately until authorized cleanup; never silently present a tiny overfiltered snapshot as complete source coverage.
- Run secret detectors with their normal contextual file pipeline. detect-secrets `scan_line` enables eager entropy search for ad-hoc strings and can classify ordinary code/docs as high-entropy candidates; it is unsuitable as a file-exclusion gate. Pin the detector version and test both ordinary source and synthetic credential cases. Record only detector types/paths, never matched values.
- For a host-local scanner that ignores approval overrides, bubblewrap can expose only the read-only snapshot/toolchain, dedicated Security home and writable results. Isolate user/PID/IPC/UTS/network namespaces. Verify production paths are absent, /source writes fail EROFS and direct IP connections fail.
- A private Unix-socket CONNECT proxy plus namespace-local loopback relay permits TLS only to explicit OpenAI hosts on443, with public-IP resolution. Verify non-OpenAI proxy requests return403 before starting. Do not widen the allowlist automatically to production targets or forward general environment secrets.
- Security CLI0.1.31 returned HTTP400 for `gpt-6.1-sol` via ChatGPT sign-in while the Hermes openai-codex route had passed separately. Provider/client capability is not interchangeable. Use the officially documented Security default `gpt-5.6-sol`/xhigh after that specific failure; leave global agent models untouched and preserve the exact failure evidence.
- Use a new output directory for every attempt. A failed scan can reserve its artifact directory even when no report files appear; reusing it returns SCAN_FAILED before inference. Preserve the failed attempt instead of deleting or overwriting it.
- A gateway terminal timeout may terminate the entire foreground scan before its own timeout/summary executes. Check process state and artifacts before retrying. For a scan longer than the foreground tool envelope, use silent background with no completion notification and consume its result through process wait/poll before ending the task; never assume a killed foreground scan will resume.
- In CLI0.1.31, `scans resume` requires a Deep Scan with a saved CLI launch recipe; Standard scans cannot be resumed even when their Codex session logs and registration persist. Reconcile process liveness, banked resets and artifacts first; reuse a already-confirmed reset instead of redeeming again. Preserve the incomplete Standard attempt and use a fresh result directory for a new Standard scan; do not switch to Deep or imply preserved coverage without approval/evidence.
- A Standard scan can seal real artifacts with manifest status=completed yet return CLI exit2 for partial coverage. Diagnose the exact CLI error and inspect coverage/manifest rather than classifying every nonzero exit as missing output or retrying indefinitely. Verify referenced artifact hashes and unique finding IDs, preserve source hashes, and distinguish declared fully reviewed files from independent coverage evidence. Static or synthetic confirmation does not establish production exploitability when runtime/allowlists/callers are excluded; request a new scope decision before inspecting excluded live context.
- Validate wrapper modes before any socket/files/model setup; reject unsupported resume modes and path-traversal mode strings instead of falling through to a fresh billable/included-usage scan. Exercise these negative guards plus the real namespace/egress contract after changing the wrapper. Keep the CLI state directory explicit under the existing dedicated home so credentials are neither relocated nor copied.
- Keep scanner stdout/stderr private. Emit only redacted status, actual finding/coverage summaries and paths. When making a snapshot Git commit, use quiet/captured output: root commits otherwise print every file and flood Discord progress.

Official sources: https://learn.chatgpt.com/docs/security/setup, https://learn.chatgpt.com/docs/security/cli, https://learn.chatgpt.com/docs/security/cli/reference.

## Current-code applicability review after a pilot

- Treat authorization to inspect current code/configuration as a separate scope from the source-only scan and from remediation. Record the exact message ID. Do not run production helpers, open .env/auth/cache/key files, call 1Password, launch another scan or spend resets merely to validate applicability.
- Build a matrix for every requested finding ID and programmatically reconcile its set/count with the sealed findings artifact. Compare snapshot/current source hashes, resolve real versus mirrored/template copies, trace current callers and read only non-secret configuration/scheduler/service metadata. Keep full evidence private outside Git; report no attack payloads.
- Separate current-route gaps, conditional direct-helper boundaries and unproven exposure. A numeric/literal lookup in a canonical caller, a per-route flock, MCP data over stdin, root-only file permissions or a legitimately supported redirect are real counterevidence; do not generalize a dangerous helper/template to all production routes. Missing callers in a bounded search do not prove retirement.
- Distinguish integrity gates from authorization proof: digest/prevalidated manifest binds content but not the human approver; atomic replace or same-request idempotency does not serialize active writes; prompt policy is not sender authentication. Check readiness ordering, object-identity binding and failure behavior before recommending a change.
- Preserve always-on approval floors as counterevidence even when approvals.mode is off. Record tool availability by configuration as availability, not as a demonstrated malicious invocation. If the read-only Discord connector omits permission overwrites, mark effective posting ACLs unknown rather than opening credentials to fetch them.
- Save per-finding conditions, source/line evidence, counterevidence and remaining uncertainty. Static review is not an incident/exploit test; distinguish completed high-severity triage from untouched medium/low findings and incomplete scan coverage. Remediation planning, isolated execution tests and production promotion remain separate authorization gates.

## Isolated remediation preparation

- Record the remediation authorization separately; prepare a frozen baseline, candidate and disposable fixture trees. Run regression checks in a no-egress namespace with a clean environment and no production homes/credential files. Keep synthetic credential/transport stand-ins explicitly labeled; they are not live authorization or endpoint evidence.
- Observe RED on the baseline, fix test-harness errors before accepting the RED receipt, then require GREEN on the candidate. Reconcile every requested finding ID to changed paths and actual test names. Report source-shape/AST contract checks separately from behavior tests; neither compilation nor string assertions proves endpoint integration.
- Generate a private unified patch, verify it with `git apply --check` against the baseline, hash the artifact and recheck the original source hashes. Never promote the patch automatically. Preserve dependencies/bootstrap excluded by the snapshot as explicit integration gaps rather than inventing fixture success or reading credentials to unblock them.
- Treat fail-closed candidate changes as compatibility gates: source-authenticated pollers must retain approved deterministic repair routes, public-download guards must cover redirects and every downloader, and approval receipts must bind issuer/actor/request/digest while keeping the signing key outside agent reach. Missing policies/keys/roots are rollout blockers, not an operationally deployed protection.

## External plugins

1. Keep experiments outside active Hermes plugins/skills, in a dedicated Codex home. ChatGPT/Codex `.codex-plugin/plugin.json` is not a Hermes plugin.yaml manifest.
2. For offline skills-only experiments use `skills: ./skills/`, focused SKILL.md and deterministic scripts for arithmetic. No MCP, credentials or public endpoint is needed.
3. Marketplace source.path resolves from marketplace root, not `.agents/plugins/`. Validate containment. Use actual host `plugin marketplace add`, `plugin add` and `plugin list` readback; inspect runtime help before using flags.
4. Compare installed script and source hashes using shell; exercise the installed copy and rejection cases. Package installation and unit tests do not prove model activation, conversational UX or public approval.
5. Record definition, prototype, installation, host activation, public submission/publication and business validation separately.
6. Consult guidelines before distribution: differentiation beyond native functions, verified identity, accurate purpose, minimum data, support/privacy/terms and at least five positive/three negative review cases. A calculator may validate packaging while being commercially undifferentiated; never promise approval.
7. Do not expose MGS panels/data/credentials or add lead capture, affiliated redirects, subscriptions or publication outside the approved scope and policy review.

Official sources: https://developers.openai.com/plugins/build/plugins, https://developers.openai.com/plugins/deploy/connect-chatgpt, https://developers.openai.com/plugins/deploy/submission, https://developers.openai.com/plugins/app-guidelines.

## Closure

Keep checkpoint/evidence pointers through MGS knowledge-control, audit/inventory and REPORT-INFRA for script/config/data changes. Report exact results and pending gates inline, no unsolicited attachments. A pending background OAuth process can write credentials after the foreground response; disclose that state rather than claiming no further writes are possible.
