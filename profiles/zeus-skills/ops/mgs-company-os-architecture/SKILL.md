---
name: mgs-company-os-architecture
description: "Use when Rodolfo asks to organize, redesign, audit, or migrate the MGS company operating structure: areas, agents, sources of truth, routing, permissions, context files, scripts, skills, docs, and safe phased restructuring before adding more agents."
tags: [mgs, company-os, architecture, operations, agents, governance, sources-of-truth, migration, inventory, zeus, atena, ares]
related_skills: [discord-ops, hermes-agent-operations, log-monitor-discord-alert]
---

# MGS Company OS Architecture

## When to use

Use this skill when Rodolfo asks about:

- Structuring the MGS as a company before creating or expanding agents.
- Reorganizing `/root/mgs-agent` outside individual agent profiles.
- Defining official areas, routes, permissions, sources of truth, and agent responsibilities.
- Turning ad-hoc scripts/docs/skills/data into a coherent operating system.
- Deciding whether files should be kept, moved, renamed, archived, consolidated, or left untouched.
- Comparing the current MGS structure with external agent/company architecture training or examples.

## Core principle

Do **not** start by moving or renaming files. Start with a blueprint and a read-only inventory.

The MGS already has real production state: sites, permissions, content pipelines, WordPress tooling, crons, logs, Hermes patches, and agent profiles. Reorganization must be incremental and reversible.

Preferred framing:

```text
We are not rebuilding from zero.
We are adding a company operating layer above the current operational foundation,
then migrating safely in small approved blocks.
```

## Canonical sequence

### 1. Read-only current-state inventory

Inspect `/root/mgs-agent` while excluding agent-specific profile content unless Rodolfo explicitly asks for it.

Default exclusions:

```text
/root/.hermes/profiles/zeus/
/root/.hermes/profiles/atena/
/root/.hermes/profiles/ares/
/root/mgs-agent/profiles/
logs/runtime-heavy files unless needed
```

Classify the structural base by top-level function:

```text
context/      conceptual company knowledge
 data/        operational data, state, inventories
 docs/        documentation, pendencies, changelog, crons
 scripts/     automations, monitors, runners, importers
 skills/      reusable procedures for agents
 patches/     local Hermes/MGS patches
 backups/     safety copies and old pre-change states
 experiments/ spikes/proofs of concept
 tools/       auxiliary tooling
 api/         internal APIs
```

### 2. Create a blueprint before operational changes

The first deliverable should usually be:

```text
/root/mgs-agent/context/company-os.md
```

Mark it clearly as a **proposal** until Rodolfo approves it as canonical.

Minimum sections:

```text
1. Objective
2. Operating principles
3. Official MGS areas
4. Agent map
5. Current sources of truth
6. Target sources of truth
7. Operational routes
8. Permissions matrix
9. File classification taxonomy
10. Safe migration plan
11. Decisions pending Rodolfo
12. Next step after approval
```

After the blueprint is in place, keep the derived docs aligned rather than letting each drift:

```text
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

If Rodolfo answers “ok” after a recommendation or execution report for a low-risk additive Company OS step, treat it as approval/continuation for that same phase/block context. If the message is a reply, anchor interpretation to the quoted message and previous execution report before acting. Still do not move/remove runtime files or alter agents without explicit scope/approval.

Discord thread discipline for Company OS work: do not rename an already-open restructuring thread while it keeps the same objective. Short messages like `Ok`, `vamos continuar`, or `prossegue` never trigger a thread rename and should inherit the current Company OS sequence until Rodolfo explicitly finalizes or changes objective.

### 3. Recommended initial MGS areas

Use the CEO-described real operating model as the starting point. The current canonical proposal is:

```text
Area                         Function
---------------------------- -------------------------------------------------
Executive / Management        Direction, strategy, priorities, daily meetings,
                              decisions, coordination and governance.
Content Operations            REC/P1, SEO support articles, categories,
                              WordPress editorial, daily content and QA.
Growth / Media Buying         Facebook Ads, Google Ads, SMS, media buyers,
                              campaign costs, acquisition and ROI.
Creative Operations           Kelly, Canva, ChatGPT, TopView.ai, Grok/other AI,
                              static/video creatives and asset handoff.
Revenue / AdOps               Smart Bidding, ActiveView, AdManager/AdX,
                              approval, ad blocks, pricing rules and AdOps.
Finance / BI                  Financial close, spreadsheets, revenue, costs,
                              invalid traffic, commissions, salaries and ROI.
Tech / WordPress / Infra      WordPress setup, plugins, pixels, VPS, Hermes,
                              agents, crons, scripts, patches and monitoring.
Security / Access             Credentials, tokens, user permissions, dashboards,
                              APIs, hardening and risk policy.
```

Durable MGS facts from the CEO explanation:
- Rodolfo and Geizian are sócios/partners. Rodolfo owns management, finance, WordPress/technical structure, pixels, partner-network relationship, strategy, and commands the AI-agent operation as a whole (not just Ares). Geizian manages the campaign/site managers day to day, launches/tests campaigns himself as gestor `g002`, and also participates in Growth, Creative support, and Revenue/AdOps.
- Ially is the office manager who follows up/cobranzas with gestores when requested tasks are late or not done.
- Raquel owns Content Operations and should supervise Atena.
- Kelly is the human owner of creative production and currently uses AI/Canva workflows for gestores. Geizian also orients/supports Kelly in Creative Operations. The creative agent name is **Hera**, not Kelly.
- There are six gestores with tracking codes used in `UTM_medium`: Icaro `g001`, Geizian `g002`, Isliago `g003`, Joe `g004`, Kelly `g005`, Nicolas `g006`.
- Geizian is both partner/coordinator and an operating gestor (`g002`): he also launches/tests campaigns for some sites.
- The campaign agent is **Ares** only. Do not use `Aris`. Do not label it `Ares futuro`; if needed, describe status separately as `em configuração` / `implantação progressiva`.
- Smart Bidding and ActiveView are Google partner companies with their own AdX/Ad Manager networks. Sites are added to those networks and ad blocks are created there before monetization starts. The Smart Bidding dashboard is the preferred/main management dashboard because it is more complete and centralizes management, even for visibility across sites.
- ActiveView is now an exception/legacy-active network: only `openzed`, `cliquet`, and their subdomains are not technologically migrated to Smart Bidding.
- Finance runs monthly: period day 1–30, Google payment around day 21–23, Rodolfo checks Facebook Business Manager spend, invalid traffic, Smart Bidding/ActiveView reports, commissions, salaries and expenses in his spreadsheet.
- Gestor compensation matters to Finance/BI: base salary is R$3,000, but commission replaces salary when higher. Commission is 7% of net profit up to R$100,000 and 10% once the gestor reaches R$100,000 net profit. Do not double-pay salary + commission.

### 4. Recommended agent map

```text
Agent   Primary area    Role
------- --------------- ------------------------------------------------------
Zeus    Executive/Ops   General Manager, governance, routing, audit, escalation;
                        controlled by Rodolfo only by default.
Atena   Content         Editorial production, REC/P1, WordPress, content QA;
                        Raquel supervises.
Ares    Growth/Ads      Campaign management, creation, analysis, acquisition;
                        Rodolfo + Geizian first, trained gestores after testing.
                        Ares does not configure ChatPion/DigitalTrChat, quiz,
                        or SMS Funnel.
Hera    Creative        Creative assets, videos, Canva/Drive organization and
                        naming taxonomy; Kelly is the human creative lead.
                        Hera and Ares both need read/write access to the
                        approved-creatives Drive so campaigns can use assets.
Future  TBD             Specialist agents created only after mission/scope exist
Future  TBD             Specialist agents created only after mission/scope exist
```

Rules:
- **Agent creation follows company architecture**. Do not create a new agent until its area, mission, sources of truth, permissions, and escalation paths are explicit.
- After a new agent is technically online, do **not** jump straight to a real operational task. First create/validate the agent's operational diagram/context document (for Hera this is `context/hera-creative-agent.md`), then align SOUL.md, create class-level skills/templates, and only then run controlled production-like tests.
- Zeus is controlled only by Rodolfo. Other company members join Zeus threads only when Rodolfo explicitly asks Zeus to include them.
- Ares starts under Rodolfo + Geizian control, then gestores get access only after the agent is tested, approved, and the gestores are trained on how to open threads and interact with it.
- The creative agent is **Hera**. Kelly is the human creative lead/gestora (`g005`), not the agent name. Rodolfo, Geizian, Kelly and gestores may request creative work according to approved scope.

### 5. Sources-of-truth distinction

Keep this separation clear:

```text
context/   explains how the company works
 data/     stores operational state and facts used by systems
 scripts/  performs deterministic actions
 skills/   teaches agents procedures
 docs/     records history, plans, pendencies, changelog
 logs/     audit/runtime trail
 patches/  local runtime modifications
```

Pitfall: do not let `SOUL.md`, ad-hoc prompts, or individual skills become the only place where company structure exists. Company architecture belongs in `context/` and is then referenced by agents.

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

When Rodolfo corrects naming or ownership (e.g. `Ares` not `Aris`, `Hera` not `Kelly agent`), search canonical context files for stale variants and clean them up. Explain that search as stale-term cleanup, not as re-litigating the user's correction.

Cascading correction rule: any correction made while reviewing one file can invalidate previously reviewed files. Before marking the current file as ready for Rodolfo review, search/patch the already-reviewed Company OS docs for conflicts, stale terms, redundant sections, duplicated governance sections, and contradictory ownership/routes. Typical cascade targets are `company-os.md`, `company-current-operating-model.md`, `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, `permissions-matrix.md`, `team.md`, `acquisition.md`, `monetization.md`, `processes.md`, `sites.md`, and the current file under review. Report the cascade explicitly in a short table. Do this **before** sending the next file for review, not after Rodolfo finds the inconsistency.

Avoid duplicating global rules inside every domain file. Conflict/source precedence belongs primarily in `sources-of-truth.md`; domain files like `sites.md` should stay focused on their content and carry only a short pointer such as “this file is conceptual; `data/sites.json` wins for automation.” If you notice a repeated `## Regra de conflito` section in a domain file, consider removing it after confirming the rule already exists in `sources-of-truth.md`.

Consistency audit rule: after applying a conceptual correction, do not only validate the current file. Run a cross-document consistency check for stale names (`Aris`, `Ares futuro`, `Kelly agent`/`agente Kelly`/`Creative Agent`), Ares overreach into ChatPion/quiz/SMS/AdOps/site setup, SB/AV ownership, gestor codes, Hera/Drive/Kelly boundaries, Ially/follow-up, and `data/sites.json` vs `sites.md` automation boundaries. Use regex/scripts as guardrails, but inspect flagged snippets semantically before reporting; negative statements like “Ares não configura ChatPion” are correct, not conflicts.

Cross-file semantic audit rule: after any material correction from Rodolfo, run a semantic consistency check across the already-touched Company OS docs. Do not rely only on `git diff --check`; whitespace validation is necessary but not sufficient. Verify naming, scope, ownership, routes, permissions, sources of truth, and finance/BI implications. If conflicts are found, patch them before asking to proceed. See `references/company-os-cross-file-consistency-audit-2026-06-06.md` for the checklist and reporting pattern.

Sequencing pitfall: after `company-current-operating-model.md` and `company-os.md` are drafted, **do not jump straight to inventory**. Review the derived files one by one with Rodolfo first: `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, and `permissions-matrix.md`. Inventory starts only after those derived docs are accepted as the current canonical proposal.

Already-reviewed-docs pitfall: before telling Rodolfo to review the five derived docs again, verify whether they were already reviewed/updated. Use session history and git/file status (`git log -- <file>`, status lines like `proposta canônica v0.x`) to distinguish “not reviewed yet” from “needs quick consistency audit.” If the docs were already worked through, do **not** restart manual review from `areas.md`; run a cross-file consistency audit, patch only real inconsistencies, mark Phase 2 as the current operational proposal, and proceed to Phase 3 inventory.

Phase 2 audit pattern after docs appear reviewed:

```text
1. Check stale terms: Aris, Ares futuro, Kelly agent, agente Kelly, Creative Agent.
2. Check required current concepts: Hera, Ares, Atena, Zeus, Smart Bidding,
   ActiveView, Geizian, Ially, gestores g001–g006.
3. Semantically inspect Ares scope flags around ChatPion/DigitalTrChat,
   quiz, SMS Funnel, AdOps/site setup and pixel setup.
4. Semantically inspect Hera scope flags around campaign execution, budget,
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
   root-sensitive files such as `.env`, `AGENT.md`, `CLAUDE.md`, and `*.bak`.
4. Separate action recommendations by class: `manter`, `não tocar`, `revisar
   depois`, `arquivar depois`, `alterar só com plano`, `append-only/consulta`.
5. Validate the inventory with required-section checks, `git diff --check`, and
   a secret scan over the diff. Then verify auto-push via `logs/auto-push.log`
   and `HEAD == origin/main` rather than assuming manual `git push` works.
6. Report Fase 3 as complete only after the repo is clean and the file is on
   origin/main.
```

Pitfall: old restructuring plans may say “next step: update company-os.md” even after that has already been done, or may duplicate “create derived docs” both before and after inventory. When reviewing the plan, update statuses and remove duplicated phases before proceeding.

Never combine broad reorganization with gateway restarts, cron rewrites, or production changes unless Rodolfo explicitly authorizes that combined scope.

### 7. Inventory deliverable format

After the blueprint, generate a migration inventory, usually under:

```text
/root/mgs-agent/docs/mgs-structure-inventory.md
```

Preferred columns:

```text
Path | Classe | Dono | Área | Status | Ação recomendada
```

Allowed actions:

```text
manter
não tocar
mover
renomear
consolidar
arquivar
remover depois
revisar com Rodolfo
```

Use `não tocar` for sensitive live state such as `data/sites.json`, `data/authorized-users.json`, active runners, active crons, and Hermes patches unless there is a specific approved plan.

Phase 3 inventory is a **risk map**, not a line-by-line content review. If Rodolfo asks what he has to review or says he does not understand the technical classification, reduce the approval question to the operating assumptions: `context/` is canonical/conceptual, `data/` is runtime, `scripts/` are productive automations, `profiles/` controls agent behavior one agent at a time, and Phase 4 should start with old `context/*.md` files before runtime/data/scripts. Give a clear COO recommendation instead of asking him to inspect every path.

When writing the inventory, include the current structural classes explicitly: `context/`, `profiles/`, `data/`, `scripts/`, `docs/`, `skills/`, `patches/`, `api/`, `tools/`, `backups/`, `experiments/`, `logs/`, and sensitive root files such as `.env`/auth/credentials. See `references/company-os-phase3-inventory-phase4-company-2026-06-07.md` for the v0.2 inventory/review pattern.

### 8. Executive communication pattern

When asking Rodolfo to review a document, do not make him infer what matters from the raw file. Default to the SOUL-style review format:

```text
1. O que faz sentido.
2. O que está demais / arriscado.
3. O que falta.
4. Pontos para Rodolfo classificar/corrigir.
```

Do **not** paste long files into chat for review. If Rodolfo asks to “show the file” or wants to read it like the screenshot example, send the current file as a native attachment (`MEDIA:/tmp/<review-file>.md`) so he can click/open it. Only paste the full file inline if he explicitly asks for inline content.

Always separate:

```text
1. What changed / current file status.
2. The 5–10 operational decisions he actually needs to validate.
3. An attached file copy when he wants to inspect the whole artifact.
```

If Rodolfo says the review is confusing, switch from file content to decision-level validation: “you only need to confirm whether these statements are true.”

```text
Arquivo: path/to/file.md

O que faz sentido
-----------------
- keep / correct operational points

O que está demais / arriscado
-----------------------------
- overlong, redundant, risky, or wrong points

O que falta
-----------
- missing concepts / rules / operational details

Pontos para Rodolfo classificar/corrigir
----------------------------------------
1. concrete decisions for Rodolfo
```

If Rodolfo asks to “show the file” or wants to read it whole, **do not paste the entire markdown into chat**. Create/send it as a native attachment (`MEDIA:/tmp/...md`) so he can click and open the full file, matching the Discord preview/card style he prefers. Use a concise note plus the attachment. Inline full-file dumps are hard to read and should be avoided unless he explicitly asks to paste content.

If Rodolfo says the review is confusing, switch from raw file content to decision-level validation: “you only need to confirm whether these statements are true.”

If Rodolfo asks to review the raw file, **send it as a `MEDIA:/absolute/path` attachment** instead of pasting long markdown into Discord. He explicitly prefers attachments for SOUL/context/skill review files; paste only short excerpts or decision tables in chat.

Good pattern:

```text
Decisão                         Confirmação
------------------------------- ------------------------------------------------
Ares                            Campanhas only; no ChatPion/quiz/SMS.
Hera                            Criativos + Drive.
Google Drive                    Source of approved creatives; Hera/Ares R/W.
```

Avoid overexplaining. Give an operational opinion and the next concrete step.

## Pitfalls

- **Moving before mapping**: creates broken imports, stale references, and agent confusion.
- **Treating current structure as garbage**: many existing MGS files are production-critical and should be wrapped, not replaced.
- **Letting agent prompts be the architecture**: prompts should consume the company OS, not be the only source of it.
- **Mixing concept and runtime**: `context/` is not `data/`; `docs/` is not `scripts/`.
- **Deleting backups/experiments too early**: classify first, archive later, delete only after explicit approval.
- **Updating agents too early**: validate blueprint with Rodolfo before changing Zeus/Atena/Ares behavior.
- **Skipping derived-doc approval**: after creating `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, and `permissions-matrix.md`, review/approve them one by one with Rodolfo before Phase 3 inventory. Do not treat the older canonical/runtime files listed inside `sources-of-truth.md` as Phase 2 manual-review targets; they belong in Phase 3 classification.
- **Over-assigning Ares**: Ares owns campaigns, not every acquisition-adjacent system. ChatPion/DigitalTrChat is configured by Rodolfo/Geizian/gestores; quiz/SMS/SMS Funnel setup is Rodolfo.
- **Duplicating source-of-truth rules everywhere**: detailed `Regra de conflito` sections belong mainly in `context/sources-of-truth.md`. Domain files like `sites.md`, `team.md`, `acquisition.md`, etc. may have a short note about their role, but avoid repeating full conflict matrices unless the file specifically governs source priority. Redundant rules make review harder and create drift.

## Referências operacionais

- `references/hera-creative-agent-bootstrap-ptbr.md` — padrão capturado na criação da Hera: sequência segura de bootstrap de agente MGS, padronização PT-BR para SOUL/docs/skills/templates e regra de anexar arquivos longos como `MEDIA:/path`.
- `references/company-os-phase3-inventory-phase4-company-2026-06-07.md` — padrão capturado na execução da Fase 3/Fase 4: inventário como mapa de risco, como explicar a revisão para Rodolfo, cobertura mínima do inventário v0.2 e padrão de primeiro bloco `context/company.md`.
- `references/company-os-thread-context-pitfall-2026-06-07.md` — correção de contexto em threads longas: thread de reestruturação mantém objetivo/nome até finalização, replies curtos herdam o bloco/fase citado, e `Ok`/`vamos continuar` não são novo assunto.

## Verification Checklist

Before reporting completion of a company-OS step:

- The deliverable exists at the declared path.
- It is clearly marked proposal/canonical as appropriate.
- No runtime file was changed unless explicitly approved.
- Sensitive sources of truth were not modified accidentally.
- Cross-file semantic consistency was checked against already-reviewed Company OS docs after any material Rodolfo correction.
- Next step is concrete and low-risk.

## References

- `references/company-os-blueprint-session-2026-06-05.md` — session-specific origin: Bruno course context, current `/root/mgs-agent` structural counts, and first blueprint pattern.
- `references/company-os-ceo-operating-model-2026-06-05.md` — CEO-described real MGS operating model: partners, Raquel/Kelly/gestores, Smart Bidding/ActiveView, finance cycle, campaigns, creative flow, and agent implications.
- `references/company-os-routes-review-2026-06-06.md` — route/scope corrections: Ares vs Hera naming, gestores/UTM codes, ChatPion/quiz/SMS boundaries, Drive creative handoff, commission model, and review sequencing.
- `references/company-os-routing-growth-creative-2026-06-06.md` — routing clarifications for Ares, Hera, gestores/UTM codes, ChatPion/DigitalTrChat/Messenger, quiz/SMS Funnel, Revenue/AdOps and gestor commission.
- `references/company-os-gestores-ares-finance-2026-06-06.md` — gestor codes (`utm_medium`), Ares staged access, Creative/Kelly agent context, Zeus-only control, and gestor commission rules for Finance/BI.
- `references/company-os-review-corrections-2026-06-06.md` — latest corrections from document review: Smart Bidding/ActiveView as Google partner AdX networks, Geizian as sócio, Ially office-manager role, Ares/Hera/Drive boundaries, and decision-level review style.
- `references/company-os-doc-review-format-sites-crons-2026-06-07.md` — review-format and cascade lessons: SOUL-style summaries, send full docs as attachments, avoid duplicated conflict sections in domain docs, sites list update/count validation, and CRONS.md generated-doc review pattern.
- `references/company-os-review-style-sites-2026-06-07.md` — review-format correction (SOUL-style summaries and full-file attachments instead of inline dumps), cascade-check expectations, and updated conceptual sites list notes.
- `references/hera-operational-architecture-bootstrap-2026-06-06.md` — sequence correction after Hera technical bootstrap: gateway online is not production-ready; create operational diagram/context doc, align SOUL, create skills/templates, then controlled tests before opening to Kelly/Geizian/gestores.
- `references/company-os-cascade-consistency-review-2026-06-06.md` — cascade consistency checklist for sequential context-file review: stale-term cleanup, Ares/Hera/SB/AV/Ially/gestor-code boundaries, and file-display pattern when Rodolfo asks to review raw content.
- `references/company-os-team-acquisition-monetization-2026-06-06.md` — approved/validated team and acquisition rewrites plus monetization v0.2 notes; includes Rodolfo's cascade-consistency expectation and verification checklist for stale/conflicting concepts.
