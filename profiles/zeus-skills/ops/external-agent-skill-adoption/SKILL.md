---
name: external-agent-skill-adoption
description: "Use when adopting external Agent Skills safely."
tags: [agent-skills, external-skills, governance, adoption, audit, mgs, google-ads]
related_skills: [hermes-agent-operations, mgs-company-os-architecture]
---

# External Agent Skill Adoption

## Purpose

Evaluate vendor/community Agent Skills without confusing documentation with operational access or importing a large catalog speculatively.

## Mandatory sequence

1. Verify the primary vendor source, current paths, license, and install syntax.
2. Define the business outcome, target platform, scope, and owning MGS agent.
3. Establish least-privilege corporate access to the real target.
4. Audit the live account/platform read-only before selecting skills.
5. Map observed needs to the smallest candidate set.
6. Inspect candidates for prerequisites, auth assumptions, stale versions, write behavior, and conflicts with MGS governance.
7. Adapt rather than blindly import when the vendor workflow is generic or harness-specific.
8. Pilot one target read-only, exercise a real query, and validate the result before expansion.

A skill is instruction/context—not credentials, authorization, an API client, an MCP server, configuration, or evidence of a successful execution. Validate those layers separately.

## Progressive disclosure

For source validation, least-privilege access, live-account discovery, candidate classification, Google Ads application, acceptance criteria, and pitfalls, load:

- `references/vendor-skill-evaluation-and-pilot.md`

## Executive reporting

Lead with: whether the claim is real, whether it applies to MGS, what live evidence is still missing, and the one next gate. Distinguish an official source from a third-party marketing funnel that cites it.

## Guardrails

- Never ask for tokens, keys, passwords, or refresh tokens in chat.
- Never bulk-install because a repository is official or popular.
- Keep billing, budget, permissions, and production writes outside discovery.
- Creating, rotating, or altering production credentials follows the applicable MGS critical authorization gate.
- Record dynamic repository counts as snapshots, not permanent facts.
