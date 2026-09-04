# Google Agent Skills — validated evaluation example

## Primary sources

- Repository: `https://github.com/google/skills`
- Launch announcement: `https://cloud.google.com/blog/topics/developers-practitioners/level-up-your-agents-announcing-googles-official-skills-repository`
- Hermes skills documentation: `https://hermes-agent.nousresearch.com/docs/user-guide/features/skills`

## Snapshot observed

At repository commit `eba988fc13cd41f23912fc3e6692a661bffbf529`:

- `skills/` tree: 130 `SKILL.md` files;
- generated `index.json`: 130 skill entries;
- plugin-embedded manifests outside `skills/`: 5;
- recursive repository total: 135 `SKILL.md` files;
- Ads category: 14 skills;
- Analytics category: 2 skills.

A public claim of “132 skills” can therefore be a time-specific count. The launch blog originally announced 13 skills. Always recount the current commit and label the count semantics.

## High-value candidates for advertising operations

- `skills/ads/google-ads-api-account-diagnostics`
- `skills/ads/google-ads-api-mcp-setup`
- `skills/ads/google-ads-api-quickstart`
- `skills/analytics/google-analytics-data-api-basics`

## Material limitations found

- The diagnostics skill expects Google Ads MCP search tools; without the MCP server it remains procedural guidance.
- The MCP setup skill requires Python 3.12+, `pipx`, Google Ads API credentials, and customer/MCC identifiers.
- The Analytics skill's default authentication guidance uses user-scoped `gcloud auth application-default login`; governed fleets may need an approved service-account adaptation instead.
- Skill installation supplies neither credentials nor API approval.
- Instructions can contain evaluation-sandbox assumptions or mandatory output formatting that should be reconciled with local policy before adoption.

## Hermes inspection pattern

Read-only discoverability can be tested with identifiers such as:

`hermes skills inspect google/skills/skills/ads/google-ads-api-account-diagnostics`

A successful result confirms resolution and parsing through the configured skill source. It is not proof of installation or operational success.

## Recommended adoption pattern

Curate individual skills instead of installing the whole repository. Start with one read-only diagnostics skill, one agent owner, one canary account, approved authentication, and a real API/MCP readback. Expand only after the canary proves correct routing, credential isolation, and useful output.
