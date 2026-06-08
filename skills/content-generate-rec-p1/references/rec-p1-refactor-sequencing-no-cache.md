# REC/P1 Refactor Sequencing and No-Cache Editorial Policy

Session: 2026-05-27 Zeus/Rodolfo/Raquel REC/P1 architecture cleanup.

## Durable lessons

1. **Do not jump from architecture docs directly to contract/SKILL edits.**
   - First create an active content map of current files, read order, runtime authority and cache influence.
   - Rodolfo explicitly corrected the process when the next step drifted between “create contract + trim SKILL” and “active content map”.

2. **REC+P1 is one business request, two technical generations.**
   - User/Raquel ask once and expect both URLs/report together.
   - Under the hood, generate/validate REC and P1 separately to preserve editorial identity.
   - Do not create a mega REC+P1 prompt or a third combined article template.

3. **Editorial card cache is not allowed for production content.**
   - `card-cache.db` can scale stale benefits, APR, descriptor, tags, image choices, or official URL across 25–30 sites.
   - Keep technical caches like WP taxonomy and QA fingerprints; remove cache as source for content/facts/images unless explicitly approved as a manual fallback.

4. **Source of truth must be narrow.**
   - Active editorial rules should live in `contracts/gb-cc-en.md`.
   - `SKILL.md` should route operations and point to the contract, not carry a long history of incident-specific rules.
   - `references/` should be historical/migration material unless a rule is promoted into the contract or runtime validators.

## Safe sequence for this class of refactor

```text
1. Active content map
2. Authority/read-order review
3. Draft/update vertical contract
4. Reduce SKILL.md to routing
5. Remove editorial cache from runners
6. Add REC+P1 orchestrator
7. Add QA semantic validator/fingerprint redesign
8. Benchmark known problem cards
```

## Active content map expected output

For each component:

```text
Path | Type | Atena reads? | Runner reads? | Current authority | Target authority | Action
```

Include at minimum:

- Atena SOUL/channel prompt if behavior is relevant;
- MGS AGENT.md;
- `content-generate-rec/SKILL.md`;
- REC/P1 templates;
- REC/P1 runners;
- card-cache scripts and DB;
- recent REC/P1 references;
- WordPress technical caches;
- fingerprint DB/script.

## Reporting pitfall

When presenting the plan, keep **one current next step**. If the sequence changes, explicitly supersede the previous next step so Rodolfo does not see conflicting process instructions.