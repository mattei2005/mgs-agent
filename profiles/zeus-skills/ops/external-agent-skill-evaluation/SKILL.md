---
name: external-agent-skill-evaluation
description: "Use when vetting external agent skills before adoption."
version: 1.0.0
metadata:
  hermes:
    tags: [skills, supply-chain, evaluation, hermes, governance]
---

# External Agent Skill Evaluation

## Purpose

Audit vendor, open-source, or community Agent Skills before installation. Establish what is official, what is marketing, which artifacts are relevant, what they actually enable, and whether they fit the live agent runtime and local governance.

A skill is primarily instructions and bundled resources. Its presence does not prove credentials, tools, API access, compatibility, authorization, or successful execution.

## When to Use

- A video, post, sales funnel, or announcement claims that a vendor released Agent Skills.
- Someone proposes installing a whole external skills repository.
- A team wants to adopt selected third-party skills into Hermes.
- An external skill prescribes authentication, MCP servers, packages, or runtime changes.
- A repository count, license, ownership claim, or installation command needs verification.

## Workflow

### 1. Recover the actual claim

If the source is video or a screen recording, use the media-processing workflow to extract metadata, representative frames, and audio when present. Record separately:

- claims made by the presenter;
- URLs or commands shown;
- product or upsell surrounding the claims;
- implied capabilities.

Do not treat a polished funnel as the vendor's official documentation.

### 2. Verify provenance with primary sources

Check the repository owner, repository URL, license, vendor announcement, and current README. Prefer the vendor's GitHub organization and official documentation/blog over reposts or marketplace descriptions.

Classify each material claim as:

- **Confirmed** — primary source and live artifact agree;
- **Outdated** — was plausible historically but live state changed;
- **Misleading** — omits a material prerequisite or overstates capability;
- **Unproven** — no primary evidence found.

### 3. Pin mutable observations

Counts and repository layouts change. For every count, capture the inspected commit SHA and distinguish:

- skills in the canonical `skills/` tree;
- entries in the repository's generated index;
- plugin-embedded `SKILL.md` files;
- total recursive `SKILL.md` files.

Never report one recursive total as though it were the vendor's canonical published skill count. Phrase counts as a snapshot, not a permanent property.

### 4. Inspect candidates before installation

Read the complete candidate `SKILL.md` plus every referenced file needed for its main path. Extract:

- intended use and exclusions;
- commands, packages, runtimes, and network requirements;
- MCP/tool dependencies;
- authentication model and required identities;
- read versus write capability;
- external endpoints and scripts;
- mandatory response-format instructions;
- assumptions tied to an evaluation sandbox or a specific agent harness.

Treat repository ownership as provenance, not as proof that every instruction fits the local environment.

### 5. Test native discoverability safely

For Hermes, prefer the native read-only inspection path before any install:

`hermes skills inspect owner/repo/path/to/skill`

A successful inspect proves only that Hermes can resolve and parse the advertised skill. It does **not** prove installation, security approval, dependencies, credentials, MCP connectivity, or an end-to-end task.

Use the current Hermes documentation for accepted identifier forms. Do not assume a generic `npx` command shown for another harness is the correct fleet installation path.

### 6. Compare with live runtime and governance

Check the target agent/profile, deployed Hermes version, language/runtime versions, available tools, identity model, credential source, and existing local skills. Flag:

- unsupported runtime requirements;
- personal OAuth or ADC where a service account is mandated;
- credentials embedded in global shell state instead of the approved secret path;
- instructions that bypass local authorization, read-only gates, audit, or ownership;
- overlap with an existing stronger local skill;
- a skill that routes work to the wrong agent.

Environment mismatches are adoption gaps to resolve, not durable claims that the external tool is broken.

### 7. Recommend a narrow pilot

Do not install an entire repository by default. Select the smallest set that supports a defined use case, then propose:

- one owner/agent;
- one canary account or non-production target;
- read-only scope first;
- explicit prerequisites;
- rollback/removal path;
- acceptance test with real readback;
- promotion criteria for broader use.

Installation or MCP/runtime configuration is a state change. Perform it only when authorized under the governing environment's policy.

### 8. Report capability precisely

Use this executive order:

1. Bottom line: real, false, or partly real.
2. What primary sources confirmed.
3. What the content oversold or omitted.
4. Practical value for the organization.
5. Exact blocker or prerequisite.
6. Recommended next action.
7. Whether anything was installed or changed.

Include direct primary-source links. Do not imply that a skill supplies account access, API approval, credentials, or autonomous execution merely because it contains operational instructions.

## Common Pitfalls

- Confusing a third-party sales page with the official vendor release.
- Repeating a mutable repository count without a commit snapshot.
- Counting plugin manifests and canonical skills as one undifferentiated total.
- Treating `inspect` as an end-to-end smoke test.
- Installing every skill because the repository is official.
- Missing user-scoped authentication instructions that conflict with enterprise identity policy.
- Calling a documentation skill an integration when the MCP/API/tool layer is absent.
- Preserving environment-specific failures as permanent prohibitions.

## Verification Checklist

- [ ] Presenter claims separated from primary-source facts
- [ ] Official repository, announcement, and license verified
- [ ] Mutable counts tied to a commit and count semantics stated
- [ ] Candidate skills and referenced files inspected
- [ ] Hermes/native resolver checked without installation
- [ ] Runtime, credentials, tools, ownership, and governance compared
- [ ] Narrow canary and real acceptance test defined
- [ ] Report states both value and limitation
- [ ] State changes, if any, explicitly disclosed

## References

- `references/google-agent-skills.md` — validated example of applying this workflow to Google's official Agent Skills repository.
