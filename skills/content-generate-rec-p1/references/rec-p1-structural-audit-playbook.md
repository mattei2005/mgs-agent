# REC/P1 Structural Audit Playbook

Use when Rodolfo asks why Atena keeps repeating REC, P1, or REC+P1 quality errors across different cards, or asks Zeus to audit the pipeline before applying fixes.

## Operating mode

- Keep the audit read-only unless Rodolfo explicitly authorizes changes.
- Do not involve or mention Atena unless Rodolfo asks; this class of task is Zeus/auditor work.
- Separate facts from recommendations: first report evidence with `path:line` and command output; only propose fixes after the diagnostic verdict is accepted.
- Treat Atena self-reports like claims, not facts. Validate against runner code, git history, DBs, logs, and WordPress state.

## Core diagnostic split

Classify each recurring issue before discussing fixes:

```text
Class                   | Examples                                      | Correct enforcement
------------------------|-----------------------------------------------|---------------------
Deterministic           | subtitle >100 chars, table columns, tags      | code hard gate: raise/exit != 0
Semi-deterministic      | repeated openings, generic copy, near clones  | post-generation validator + regenerate/abort
Subjective/editorial    | tone, commercial feel, human voice            | prompt/rubric + human calibration
```

Do not accept `.md` references as hard gates. A real gate is runtime code that blocks publication or returns non-zero status.

## Audit sections

### A — Hard gates in runners

Inspect:
- `/root/mgs-agent/scripts/mgs-rec-runner.py`
- `/root/mgs-agent/scripts/mgs-p1-runner.py`

Report:
- count of `raise`, `assert`, `sys.exit`
- line/context for each important `RunnerError`
- which gates run before article generation vs after generation vs after publish
- gaps between Raquel/Rodolfo complaints and actual runtime gates

Known baseline from 2026-05-27 audit:

```text
File                                  | raise | assert | sys.exit
--------------------------------------|-------|--------|---------
scripts/mgs-rec-runner.py              | 46    | 0      | 0
scripts/mgs-p1-runner.py               | 35    | 0      | 0
```

Interpretation: the problem is not absence of all hard gates; it is incomplete coverage, especially semantic repetition and editorial identity.

### B — Where recent fixes landed

Git author filtering may be misleading because `/root/mgs-agent` commonly records commits as `Rodolfo Mattei` even when auto-committed from agent work. Prefer classifying by changed files and commit subject.

Classify commits into:

```text
Layer | Meaning
------|--------
A     | hardcoded prompt/string in `.py` that affects generation
B     | Python logic/validators/flow around generation
C     | `.md` references/skills/docs; useful for humans, inert unless runner reads them
D     | data/cache/WordPress/post-specific repair; fixes one run or runtime state
```

Known baseline from 2026-05-27 read-only audit over recent REC/P1 files:

```text
Layer grouping                         | Relevant commits
---------------------------------------|-----------------
A/B .py runner/prompt/logic             | 16
C .md/reference                         | 25
D data/cache/auth/inventory             | 9
Total analyzed                          | 42
```

Interpretation: Atena had changed both `.py` and `.md`; do not falsely say it only edited Markdown. The durable concern is fragmentation and reactive patching, not zero code changes.

### C — REC ↔ P1 coupling

Check whether P1 shares LLM/session context with REC and whether it reads REC content/metadata.

Known baseline from `mgs-p1-runner.py` on 2026-05-27:
- Lines around 797-810 load REC by URL/post ID and read `content.raw`, `content.rendered`, and title.
- `parse_card_from_rec()` parses the REC LazyBlock for card name, image URL/id, tags and descriptor.
- Lines around 837-841 preserve REC LazyBlock labels/descriptor when official extraction is generic.

Interpretation: there was no evidence of shared LLM session context, but there is real structural coupling: P1 depends on REC metadata/image/slug and can inherit weak REC labels/descriptors. Also, P1 body generation is heavily deterministic/template-like, which can create formulaic copy even without shared LLM context.

### D — Anti-duplication/fingerprint

Inspect `/root/mgs-agent/scripts/rec-fingerprint.py` and runner calls.

Known baseline from 2026-05-27:
- Algorithm: normalize HTML/text, build 5-word shingles, Jaccard similarity.
- Default threshold: `0.35`.
- Query scope: `WHERE card_slug=? AND site_key<>?`.
- Runner calls it in `mgs-rec-runner.py`; `mgs-p1-runner.py` did not call it.
- It is designed for same-card multi-site duplicate detection, not same-site repeated openings across different cards.

Interpretation: it will not catch Raquel's complaint class: generic phrases repeated across different cards, nor P1 similarity.

### E — References `.md`

List references under `/root/mgs-agent/skills/content-generate-rec-p1/references/`, recent modifications, and grep runners for exact reference filenames.

Known baseline from 2026-05-27:
- 53 reference `.md` files existed.
- No exact reference filename match was found in the REC/P1 runners.

Interpretation: references are valuable documentation, but they do not affect runtime unless their rules are encoded in runner prompts, validators, or scripts.

## Reporting style

Use concise executive blocks. Lead with verdict, then evidence. Example:

```text
Veredito preliminar

Ponto                              | Achado
-----------------------------------|--------------------------------------------------
Hard gates existem?                | Sim, mas não cobrem semântica/repetição
P1 lê REC?                         | Sim: raw/rendered + LazyBlock metadata
Fingerprint pega o problema?       | Não: só mesmo card_slug entre sites
Escala para 30 sites?              | Não sem validators/hard gates adicionais
```

End with `Próximo passo pendente:` naming the next audit or approval gate, especially if changes are not yet authorized.
