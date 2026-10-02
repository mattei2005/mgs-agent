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
3. Use an environment allowlist without 1Password, SSH, cloud or API keys. Explicit `--auth chatgpt` prevents headless auto-auth from choosing a billable key. Require user-mediated login and verified access; package availability does not establish entitlement. Trusted Access for Cyber may be required.
4. Keep outputs private and outside the repository. `--dry-run` validates local inputs only: no credential loading, access verification, code analysis or security findings. Label it preflight.
5. Report-only is not filesystem isolation. Official scans use local permissions, approvalPolicy=never and a fixed filesystem profile; --codex cannot restrict these controls. Require separately validated OS-level sandbox/source snapshot, no production secrets and isolated artifact writes before scanning. Never scan the operational worktree directly as root.
6. No --mock as evidence, --patch, --create-pr, Git hooks or production calls for a read-only pilot. Review findings, validation evidence and coverage complete/partial/unknown. No report means no completed scan. Do not send raw scanner logs to Discord.
7. Credentials, GitHub grants, billing and permission changes remain subject to MGS confirmation gates. State the exact blocker and scope; never claim dry-run substitutes for the authorized pilot.

Official sources: https://learn.chatgpt.com/docs/security/setup, https://learn.chatgpt.com/docs/security/cli, https://learn.chatgpt.com/docs/security/cli/reference.

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
