# REC/P1 Active Content Map Before Refactor

Session lesson from Rodolfo/Zeus REC+P1 architecture discussion.

## Trigger

Use this reference when restructuring REC, P1, REC+P1, `SKILL.md`, contracts, templates, runners, cache, or references because the system has accumulated too many active-looking instruction layers.

## Key correction from Rodolfo

Do **not** jump from target architecture directly to creating `contracts/gb-cc-en.md` and trimming `SKILL.md`.

Correct sequence:

```text
1. Active content map of current files
2. Real read/authority order
3. Extract useful rules and conflicts
4. Create/approve `contracts/gb-cc-en.md`
5. Then trim `SKILL.md`
6. Then remove editorial cache from runners
7. Then add REC+P1 orchestrator / QA validator
```

If you skip step 1, the process becomes confusing because you may edit the wrong authority layer.

## Active content map output shape

Produce a table like:

```text
File/Component | Type | Who reads it | Runtime effect | Current authority | Target authority | Action
```

Minimum components to map:

- Atena `SOUL.md`
- MGS `AGENT.md`
- Atena Discord channel prompt
- `skills/content-generate-rec-p1/SKILL.md`
- `templates/rec-gb-cc-en.md`
- `templates/p1-gb-cc-en.md`
- `scripts/mgs-rec-runner.py`
- `scripts/mgs-p1-runner.py`
- `skills/content-generate-rec-p1/scripts/card-cache-*`
- `data/card-cache.db`
- `data/wp-term-cache.json`
- `data/rec-fingerprints.db`
- recent REC/P1 references that look active

## Authority principle

Separate these categories explicitly:

```text
Runtime active       = Python runners/scripts that directly affect output
Editorial contract   = one approved source of truth per vertical
Operational routing  = short SKILL instructions telling Atena what to run
Historical reference = incident lessons, not active production rules
Technical cache      = IDs/config/fingerprint, not article facts or copy
Editorial cache      = must not feed production content
```

## Cache policy captured in this session

Rodolfo's preference and Zeus recommendation converged:

- No editorial cache in content production.
- Do not let `card-cache.db` provide benefits, fees, APR, descriptors, tags, headlines, or body copy.
- For same card across 25+ sites, fetch current official facts and generate fresh copy per site.
- Keep only technical/non-editorial caches such as WordPress term IDs and QA fingerprints.

## REC+P1 separation principle

Business operation stays unified: one REC+P1 request should deliver both posts and one final summary.

Technical production should be separated:

```text
single REC+P1 request → orchestrator → REC runner → allowed metadata → P1 runner → combined validation/report
```

P1 should not ingest REC paragraphs/opening/benefit prose as editorial input.

## Pitfall

Do not tell Rodolfo "next step is Checkpoint A: create contract + trim SKILL" immediately after saying an active content map is needed. That confuses the process. The active content map is the next step before any edit.