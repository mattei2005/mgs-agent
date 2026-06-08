# REC+P1 — WordPress taxonomy/tags review (2026-06-08)

## Trigger

During the Atena REC+P1 restructuring review, Rodolfo asked where WordPress tags are included before running the first real draft test. The review found that tags were technically being sent to WordPress by both runners, but the active REC+P1 skill did not clearly distinguish WordPress taxonomy tags from LazyBlock visual tags, and the P1 runner had a risky commercial default.

## Files involved

- `/root/mgs-agent/skills/content-generate-rec-p1/SKILL.md`
- `/root/mgs-agent/scripts/mgs-rec-runner.py`
- `/root/mgs-agent/scripts/mgs-p1-runner.py`
- `/root/mgs-agent/skills/content-publish-wordpress/scripts/resolve-term.sh`

## Correct model

WordPress tags are operational post taxonomy. They are not the same thing as the two visual benefit tags shown inside the card LazyBlock.

Required WordPress tags for REC/P1:

```text
- rec or p1
- vertical, e.g. cc
- country, e.g. gb
- clean card/product tag
- lang_<language>, e.g. lang_en
- atena_agent
```

Commercial tags are optional and must be supported by confirmed facts from the current official source or current request:

```text
- no annual fee
- cashback rewards
- rewards credit card
- travel credit card
- avios rewards
- airport lounge access
- balance transfer
- purchase credit card only for confirmed 0%, interest-free, introductory or promotional purchase offers
- issuer, e.g. hsbc / barclaycard / lloyds
```

## Pitfall fixed

The P1 runner previously appended `rewards credit card` by default through `c["tags"][0]`, even when the product did not have a confirmed rewards/cashback/points benefit. That could misclassify non-rewards cards in WordPress.

Correct behavior:

- Do not add `rewards credit card` unless benefits contain rewards/cashback/points evidence.
- Do not add `purchase credit card` just because copy contains generic words like “everyday purchases”. Only add it for confirmed promotional purchase offers such as 0%, interest-free, introductory or promotional purchase terms.
- Keep `atena_agent` and `lang_<language>` as hard validation requirements.

## Verification pattern

Use monkeypatch/unit probing to test taxonomy derivation without touching WordPress:

1. Import `mgs-p1-runner.py` and monkeypatch `resolve_term` to return deterministic IDs.
2. Import `mgs-rec-runner.py` and monkeypatch `resolve_term_id` to return deterministic IDs.
3. Validate these cases:
   - No-annual-fee everyday-purchase card: should include `no annual fee`; should not include `rewards credit card`; should not include `purchase credit card`.
   - Confirmed 0%/introductory purchase card: should include `purchase credit card`.
   - Rewards/travel/Avios card: should include the corresponding commercial tags.
4. Run `python3 -m py_compile` on REC/P1 runners and orchestrator.
5. Run `git diff --check` on changed files.

## Operational lesson

Before a first real REC+P1 draft after contract changes, review the runners for the exact WordPress payload fields, not just the editorial contracts. A contract rule only matters operationally if the runner writes the corresponding `post_json` and the final JSON exposes evidence for the report.
