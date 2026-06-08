# Atena REC/P1 contract v2 and runner migration gate — 2026-06-08

## Trigger

Rodolfo sent revised `rec.txt` and `p1.txt` from Raquel and asked Zeus to compare them against Atena `SOUL.md`, `SKILL.md`, and the active REC/P1 contracts.

## Decisions from Rodolfo

- P1 keyword count: keep the new contract value, **5 to 8** occurrences.
- REC meta description: change to **130 to 140 characters**.
- REC structure: keep the new structure because the prior runner/contract was over-specifying example benefits, and Atena treated examples as allowed-only benefits.
- P1 structure: keep the new structure, with an explicit note that P1 must deepen what the card actually offers instead of repeating generic REC phrasing.
- P1 LazyBlocks: correct as designed; the repeated asset is the isolated **card image**, reused in REC and P1 LazyBlocks.
- REC slug: use the clearest machine-readable pattern: `rec-{sigla-do-pais}-cc-{nome-do-cartao}`.
- P1 slug: correct example to `apply-now-gb-cc-aib-visa-gold`.
- Featured image: move long visual composition rules out of the main contracts into a reference, with concise gates in REC/P1 contracts.

## Applied paths

```text
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md
/root/mgs-agent/skills/content-generate-rec-p1/references/featured-image-visual-contract.md
```

Commit observed in-session: `e442ae0`.

## Durable lesson

When Rodolfo/Raquel revise editorial contracts, do **not** stop at replacing the markdown. Compare the new contract against the deterministic runners and validators. If the contract promises a structure the runner does not yet emit, report that as a migration gate before production use.

## Runner migration checklist

Before declaring Atena REC+P1 v2 production-ready, validate and patch:

```text
Area                  Required check
--------------------  ---------------------------------------------------------
REC structure          Runner emits new REC structure: H3 benefits, points to
                       consider, profile/recommended section, pros/cons, final
                       section and final internal CTA.
REC examples           Contract/runner do not treat example benefit categories
                       as allowed-only content. Benefits must come from the
                       actual card and official/request facts.
REC meta               Validator enforces 130-140 characters.
P1 keyword             Validator enforces 5-8 keyword occurrences.
P1 Details             Runner emits WordPress Details blocks for Benefits,
                       Who should use, APR/taxes/costs, and Requirements when
                       applicable.
P1 benefit depth       Runner text deepens actual card offers, practical impact,
                       mechanics and usage scenarios; it must not recycle REC
                       phrasing or generic boilerplate.
P1 LazyBlock           Card image may be reused from REC LazyBlock; button/link
                       points to official issuer/partner URL and siteout says
                       the user will be redirected.
Images                 REC and P1 featured images are different; P1 internal
                       image may reuse the P1 featured image.
Slug                   REC uses `rec-{country}-cc-{card}`; P1 uses
                       `apply-now-{country}-cc-{card}`.
```

## Reporting pattern

Use this distinction in future reports:

```text
Contract editorial     Updated/approved as editorial source of truth.
Runner compatibility   Separate technical gate; not implied by contract update.
Production readiness   Only after runner/validator dry-run and draft test pass.
```

Do not publish a real REC+P1 under the v2 contract until the runner compatibility gate is closed or the report clearly says the run is a controlled test of the migration.