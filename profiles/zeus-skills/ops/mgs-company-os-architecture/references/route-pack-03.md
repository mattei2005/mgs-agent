### 6. Safe migration stages

Use staged gates. If `company-current-operating-model.md` and `company-os.md` already exist, do **not** keep using the generic initial order; first reconcile the plan/status with the actual completed artifacts.

Recommended current-stage sequence:

```text
Phase 0   Capture real operating model    company-current-operating-model.md
Phase 1   Company OS blueprint             company-os.md, marked proposal/canonical as appropriate
Phase 2   Derived canonical context docs   areas, agent-map, routes, sources-of-truth, permissions
Phase 3   Classified inventory             one line per relevant path
Phase 4   Migration plan by block          explicit action/risk per file or folder
Phase 5   Agent reference updates          one agent at a time, validated after each
Phase 6   Operational validation           Discord, logs, crons, agents, runtime
Phase 7   Cleanup/archival                 explicit Rodolfo approval per block
```

When Rodolfo says to review files one by one, do **not** jump to inventory or migration. Present the current file, accept corrections, patch it, then move to the next.

In a long-running Company OS restructuring thread, preserve thread context aggressively. If Rodolfo replies with a short acknowledgement such as “Ok”, “continue”, “vamos continuar”, or “próximo”, inherit the quoted/recent block context and execute the next recommended low-risk block. Do not treat the message as a new topic, do not re-plan from scratch, and do not rename the existing thread while the objective is still the same.

Long-running Company OS threads have persistent objective continuity. A short reply such as “ok”, “continue”, or “vamos continuar” usually approves/continues the current block; if it is a Discord reply, use the quoted/replied message as the primary context anchor. Do not reinterpret a short reply as a new topic, and do not rename an already-open restructuring thread while the objective is still the same. Thread title changes belong only at thread creation or after an explicit, strong topic change — never from a vague message or reply.

When Rodolfo corrects naming or ownership (e.g. `Ares` not `Aris`, `agente legado` not `Kelly agent`), search canonical context files for stale variants and clean them up. Explain that search as stale-term cleanup, not as re-litigating the user's correction.

Cascading correction rule: any correction made while reviewing one file can invalidate previously reviewed files. Before marking the current file as ready for Rodolfo review, search/patch the already-reviewed Company OS docs for conflicts, stale terms, redundant sections, duplicated governance sections, and contradictory ownership/routes. Typical cascade targets are `company-os.md`, `company-current-operating-model.md`, `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, `permissions-matrix.md`, `team.md`, `acquisition.md`, `monetization.md`, `processes.md`, `sites.md`, and the current file under review. Report the cascade explicitly in a short table. Do this **before** sending the next file for review, not after Rodolfo finds the inconsistency.

Avoid duplicating global rules inside every domain file. Conflict/source precedence belongs primarily in `sources-of-truth.md`; domain files like `sites.md` should stay focused on their content and carry only a short pointer such as “this file is conceptual; `data/sites.json` wins for automation.” If you notice a repeated `## Regra de conflito` section in a domain file, consider removing it after confirming the rule already exists in `sources-of-truth.md`.

Consistency audit rule: after applying a conceptual correction, do not only validate the current file. Run a cross-document consistency check for stale names (`Aris`, `Ares futuro`, `Kelly agent`/`agente Kelly`/`Creative Agent`), Ares overreach into ChatPion/quiz/SMS/AdOps/site setup, SB/AV ownership, gestor codes, agente legado/Drive/Kelly boundaries, Ially/follow-up, and `data/sites.json` vs `sites.md` automation boundaries. Use regex/scripts as guardrails, but inspect flagged snippets semantically before reporting; negative statements like “Ares não configura ChatPion” are correct, not conflicts.

Cross-file semantic audit rule: after any material correction from Rodolfo, run a semantic consistency check across the already-touched Company OS docs. Do not rely only on `git diff --check`; whitespace validation is necessary but not sufficient. Verify naming, scope, ownership, routes, permissions, sources of truth, and finance/BI implications. If conflicts are found, patch them before asking to proceed. See `references/company-os-cross-file-consistency-audit-2026-06-06.md` for the checklist and reporting pattern.

Sequencing pitfall: after `company-current-operating-model.md` and `company-os.md` are drafted, **do not jump straight to inventory**. Review the derived files one by one with Rodolfo first: `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, and `permissions-matrix.md`. Inventory starts only after those derived docs are accepted as the current canonical proposal.

Already-reviewed-docs pitfall: before telling Rodolfo to review the five derived docs again, verify whether they were already reviewed/updated. Use session history and git/file status (`git log -- <file>`, status lines like `proposta canônica v0.x`) to distinguish “not reviewed yet” from “needs quick consistency audit.” If the docs were already worked through, do **not** restart manual review from `areas.md`; run a cross-file consistency audit, patch only real inconsistencies, mark Phase 2 as the current operational proposal, and proceed to Phase 3 inventory.

Phase 2 audit pattern after docs appear reviewed:

```text
1. Check stale terms: Aris, Ares futuro, Kelly agent, agente Kelly, Creative Agent.
2. Check required current concepts: agente legado, Ares, Atena, Zeus, Smart Bidding,
   ActiveView, Geizian, Ially, gestores g001–g006.
3. Semantically inspect Ares scope flags around ChatPion/DigitalTrChat,
   quiz, SMS Funnel, AdOps/site setup and pixel setup.
4. Semantically inspect agente legado scope flags around campaign execution, budget,
   pixel and Business Manager.
5. Patch only ambiguous or conflicting language.
6. Update `docs/mgs-os-restructure-plan.md` to show Fase 1/Fase 2 as
   “concluída como proposta operacional atual” when the audit passes.
7. Register a concise audit event and validate with `git diff --check`.
```

Phase 3 inventory pattern:

```text
1. Before generating inventory, clean unrelated repo dirt that could contaminate
   the next block. If `profiles/zeus-skills/...` is dirty, review it as a
   separate hygiene block, keep useful skill/procedure updates, fix obvious
   renames, run a secret scan, commit/push, then continue.
2. Treat `docs/mgs-structure-inventory.md` as read-only classification only:
   no moves, no deletes, no runtime writes.
3. If the inventory file already exists, update it in place instead of creating
   a duplicate. Include current counts for top-level areas and classify:
   `context/`, `profiles/`, `data/`, `scripts/`, `docs/`, `skills/`,
   `patches/`, `api/`, `tools/`, `backups/`, `experiments/`, `logs/`, and
   root-sensitive files such as `.env`, `AGENT.md`, and `*.bak`.
4. Separate action recommendations by class: `manter`, `não tocar`, `revisar
   depois`, `arquivar depois`, `alterar só com plano`, `append-only/consulta`.
5. Validate the inventory with required-section checks, `git diff --check`, and
   a secret scan over the diff. Then verify auto-push via `logs/auto-push.log`
   and `HEAD == origin/main` rather than assuming manual `git push` works.
6. Report Fase 3 as complete only after the repo is clean and the file is on
   origin/main.
```

Phase 4 context-file/block pattern:

```text
1. Work one approved block at a time; for context files, change conceptual docs
   only unless Rodolfo explicitly expands scope.
2. After every material correction, run cross-file semantic checks for stale
   names, Ares/agente legado boundaries, SB/AV exceptions, gestor codes, Finance/BI and
   source-of-truth conflicts.
3. Report each block with: arquivo principal, status/version, validation, secret
   scan, audit log, auto-push, HEAD=origin, and repo state.
4. If Rodolfo says “ok continue”, immediately proceed to the next recommended
   block. Do not ask him to restate the plan.
5. After `docs/CRONS.md` / Bloco 7, update `docs/mgs-os-restructure-plan.md` to
   mark the completed blocks and define the Fase 5 gate before changing agents.
```

Phase 5 Zeus SOUL alignment pattern:

```text
1. First gate is Zeus only unless Rodolfo explicitly expands scope.
2. Patch both live and versioned SOUL files:
   /root/.hermes/profiles/zeus/SOUL.md
   /root/mgs-agent/profiles/zeus-soul.md
3. Create timestamped backups before editing and keep live/versioned files identical.
4. Add a top-level `MGS OS — fonte gerencial principal` section that points Zeus
   at `/root/mgs-agent/context/` and relevant runtime/docs sources instead of
   duplicating all company architecture inside SOUL.
5. Encode source precedence: data/runtime/logs/WordPress/crontab/services for
   live technical state; context/MGS OS for managerial structure; SOUL for
   posture/channel/safety/behavior.
6. Clean stale wording while there: no `futuramente Ares`; no hardcoded stale
   model identity like `Claude Sonnet` when MGS policy says GPT-5.5/OpenAI-Codex.
7. Update `docs/mgs-os-restructure-plan.md` to mark Zeus concluded and the next
   agent gate, normally Atena.
8. Validate: diff check, secret scan on added lines, stale-term scan, live/versioned
   cmp, audit log, auto-push, HEAD=origin, repo clean.
9. Do not touch crontab, tokens, runtime/systemd, permissions, cleanup/migration,
   or Discord thread title in the initial Zeus gate.
```

Detailed runbook: `references/company-os-phase5-zeus-soul-alignment-2026-06-07.md`.

Phase 5 agent HOT operational map pattern:

```text
1. When an agent repeatedly performs broad `search_files` calls for generic
   operational terms (`drive`, `creative`, `meta`, `UPLOAD`, `CC_*`, etc.), add
   a compact HOT map under `/root/mgs-agent/context/<agent>-operational-map.md`.
2. The HOT map should route natural-language asks to first canonical sources:
   context docs, SOUL, class-level skills, runtime data, scripts, logs, handoff
   rules, boundaries and validation checks.
3. Patch `/root/mgs-agent/context/mgs-os-map.md` so Zeus knows the new map, and
   patch both live + versioned SOUL files with a short pointer instructing the
   agent to open the HOT map before broad search.
4. Validate live/versioned SOUL equality, `git diff --check`, secret scan, audit
   log, gateway restart if SOUL changed, service active state, auto-push and
   `HEAD == origin/main`.
5. Do not roll out automatically to agents whose operating model is being
   rebuilt. If Rodolfo excludes an agent such as Atena during reconstruction,
   leave it untouched.
```

Detailed runbook: `references/agent-hot-operational-maps-2026-06-16.md`.

Phase 5 agente legado Creative Ops alignment pattern:

```text
1. Do not frame agente legado as an assistant/subagent of Ares. agente legado owns Creative
   Operations: creating static/video creatives, receiving human-created assets,
   organizing Drive/naming/inventory, and supporting both Ares and humans.
2. Ares is an optional consumer of approved assets, not the mandatory path for
   every creative. Kelly, Geizian and gestores may create or use creatives
   directly in campaigns; agente legado still keeps assets organized.
3. Do not impose a rigid creative request form. Users should ask naturally in
   the agente legado channel. agente legado infers safely, asks only blocking questions, and the
   skill evolves from real usage.
4. Treat `CC_US_ES` as an example/pilot taxonomy aligned with Ares, not the only
   Drive operation. MGS-AGENTS/CRIATIVOS is multivertical; agente legado must route each request
   or upload to the correct vertical/operation folder.
5. For multivertical naming, use the general model
   `{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}`
   and adapt per operation as the real workflow stabilizes.
6. Inventory should track origin and consumer, at minimum: `created_by`,
   `requested_by`, `used_by`, `campaign_owner`, and `source`.
7. Creative metadata is a first-class handoff gate: agente legado should clean assets
   before Drive/handoff, and Ares should verify/clean before campaign use. The
   canonical wrapper is `/root/mgs-agent/scripts/clean-creative-metadata.sh`;
   avoid deploying ExifCleaner/Electron on the VPS for agent workflows.
8. When aligning agente legado files, patch live + versioned SOUL/skill/templates, verify
   live/versioned equality, validate with `git diff --check` and secret scan,
   restart/reload `legacy-agent-gateway.service` when SOUL changes, confirm Discord
   connected, and audit log.
```

Detailed runbooks: `references/legacy-agent-creative-ops-natural-requests-2026-06-07.md` and `references/creative-metadata-sanitizer-legacy-agent-ares-2026-06-08.md`.

Phase 5 Atena reconstruction gate pattern:

```text
1. Do not apply the Zeus SOUL-alignment pattern directly to Atena. Atena is a
   production content agent with REC/P1/REC+P1, WordPress, images, Yoast,
   runners, contracts and historical bug references.
2. Before patching Atena, read the prior Atena reconstruction thread when
   Rodolfo references it (known thread id: 1512539907468558477) and reconcile
   what was approved there with the live VPS state.
3. Treat Atena's rebuild as layer separation, not a full code rewrite:
   SOUL = identity/governance; SKILL = operating procedure; contracts = article
   product specs; scripts/runners = factory/implementation; references =
   historical lessons to archive/distill, not active competing rules.
4. SOUL additions should stay high-level: Content Operations, Raquel supervision,
   complete request means authorization, escalation to Zeus, and boundaries
   against campaigns/creative/AdOps/infra/permissions/finance.
5. Never put runner commands, Yoast char limits, slug logic, WordPress steps,
   image implementation details, or long bug-history lessons into SOUL. Put them
   in SKILL/contracts/code validations as appropriate.
6. When patching Atena SOUL, keep live and versioned files identical:
   `/root/.hermes/profiles/atena/SOUL.md` and
   `/root/mgs-agent/profiles/atena-soul.md`. Create timestamped rollback backups
   for both before editing.
7. If the current SOUL lists stale skill status such as `content-generate-p1` or
   `content-generate-rec-and-p1` as “em desenvolvimento”, replace that with a
   layer statement: detailed operations live in `content-generate-rec`,
   `content-publish-wordpress`, contracts and runners. SOUL must not become a
   brittle feature/status registry.
8. After a SOUL-only alignment, validate at minimum: live/versioned cmp,
   `git diff --check`, secret scan on added lines, stale skill-status scan,
   audit log, auto-push and `HEAD == origin/main`.
9. If Rodolfo asks whether Atena should be notified, post a concise operational
   note in the Atena reconstruction thread explaining what changed and what did
   not change, then continue review there. Do not create a second parallel design
   thread.
10. For Atena SOUL authorization language, keep the article-request flow simple:
    Rodolfo and Raquel can request content by default. If anyone else requests
    an article, Atena should ask Rodolfo whether that person may request it,
    summarizing requester + requested article/product + site/status + official
    URL when available. The authorization options should be: `uma vez só`,
    `somente nesta sessão/thread`, or `sempre autorizada`; when the interface
    supports it, present those as buttons. Avoid overcomplicating this in SOUL
    with broad permission-matrix detail; detailed permissions live in MGS OS.
11. Rodolfo should continue design/review in the Atena reconstruction thread,
    mark files explicitly approved (`SOUL aprovado`, `SKILL aprovado`, etc.),
    then ask Zeus to read/apply. Zeus cannot assume live cross-thread context.
11. Only apply deeper SKILL/contracts changes after backup + diff + secret scan +
    audit log + auto-push + validation, preserving runners/scripts unless a
    specific targeted bug fix is approved.
12. If Rodolfo/Raquel approve new REC/P1 editorial contracts, do not stop at
    writing `contracts/cc-rec.md` and `contracts/cc-p1.md`. Immediately map and
    patch the deterministic runners/validators that must honor those contracts
    before declaring the phase ready for production. Contract-runner drift is a
    real operational risk.
13. For the current REC/P1 contract v2 baseline: P1 keyword count is 5–8 visible
    editorial uses; REC meta is 130–140 chars; P1 meta is 130–150 chars; P1 uses
    Details blocks; the card image can repeat in REC/P1 LazyBlocks but featured
    images must differ; long image composition rules belong in a reference file,
    not duplicated inside every contract.
14. When applying Atena SOUL Phase 1 packages, validate the content against the
    latest Rodolfo correction before applying — not just bash syntax, SHA, line
    count, or secret scan. The current simple article-request authorization model
    is: Rodolfo/Raquel execute directly; anyone else triggers a Rodolfo approval
    choice with three options: `Uma vez só`, `Somente nesta sessão`, or `Sempre
    autorizada` (buttons when supported). Avoid staging temporary SOUL files under
    `/root/mgs-agent/profiles/` because auto-commit may version them before
    cleanup; use `/tmp` for staging and write only final live/versioned files.
    See `references/atena-soul-phase1-application-2026-06-12.md`.
```
    contract against live deterministic runners/validators before calling the
    system production-ready. A contract update is an editorial source-of-truth
    change; runner compatibility is a separate technical gate.
13. If the new contract requires structures the runner does not yet emit
    (e.g. REC H3 benefits/pros-cons/final CTA, P1 WordPress Details blocks,
    P1 5-8 keyword occurrences, REC meta 130-140 chars), apply the contract
    first only if approved, then report the runner migration as the next phase
    before any real production REC+P1.
```

Detailed runbook: `references/company-os-phase5-atena-reconstruction-thread-2026-06-07.md`.

CRONS.md review pattern:

```text
1. Treat `docs/CRONS.md` as generated documentation from the live root crontab.
2. Do not alter crontab/runtime during documentary review unless explicitly
   authorized.
3. If generated content is stale/wrong, patch `scripts/cron-control-plane.py`
   metadata first, then regenerate `docs/CRONS.md`.
4. Validate: total jobs, all jobs use flock, no `não classificado`, no `Sem
   descrição cadastrada`, `git diff --check`, secret scan on added lines, audit
   log, auto-push, HEAD=origin.
5. Known correction: `cleanup-zombie-sessions.sh` uses last real activity with
   default 180min grace, not the older 30min description.
```

Pitfall: old restructuring plans may say “next step: update company-os.md” even after that has already been done, or may duplicate “create derived docs” both before and after inventory. When reviewing the plan, update statuses and remove duplicated phases before proceeding.

Never combine broad reorganization with gateway restarts, cron rewrites, or production changes unless Rodolfo explicitly authorizes that combined scope.

