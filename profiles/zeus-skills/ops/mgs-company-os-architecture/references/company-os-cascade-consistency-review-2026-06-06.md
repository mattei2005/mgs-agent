# Company OS cascade consistency review — 2026-06-06

## Session learning

During sequential review of MGS context files, Rodolfo explicitly corrected the workflow: a correction in the current file can invalidate previously reviewed files, so Zeus must not treat approvals as isolated. After each conceptual correction, run a cascade check across already-reviewed Company OS documents before moving on.

## Files involved in this review class

Core Company OS docs:

```text
context/company.md
context/company-os.md
context/company-current-operating-model.md
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

Extended review docs once Phase 3 begins:

```text
context/team.md
context/acquisition.md
context/monetization.md
context/processes.md
context/sites.md
docs/mgs-structure-inventory.md
```

## Durable operational facts reinforced

- Rodolfo commands the AI-agent operation as a whole, not just Ares.
- Zeus is controlled by Rodolfo only by default; others join Zeus threads only if Rodolfo asks.
- Geizian is Rodolfo's sócio and also operating gestor `g002`.
- Ially is Office / Follow-up: she cobras/accompanies pending gestor tasks and escalates to Geizian/Rodolfo.
- Ares is campaign/Growth agent only; do not write `Aris`, `Ares futuro`, or assign ChatPion/quiz/SMS setup to Ares.
- agente legado is the creative agent. Kelly is a human gestor/creative lead `g005`, not the agent.
- agente legado and Ares can read/write the approved-creatives Google Drive; Kelly/humans approve when needed.
- ChatPion/DigitalTrChat: Rodolfo + Geizian create users; gestores configure operational flows; no Ares.
- Quiz/SMS/SMS Funnel: Rodolfo configures; no Ares.
- Smart Bidding and ActiveView are Google partner companies with their own AdX/Ad Manager networks. SB dashboard is preferred/main; AV remains active exception for `openzed`, `cliquet`, and subdomains.
- `data/sites.json` is technical source for automation; `context/sites.md` is conceptual portfolio context.

## Cross-document consistency checklist

Before saying a reviewed file is aligned, check at least:

```text
No stale names: Aris, Ares futuro, Kelly agent, agente Kelly, Creative Agent.
No stale creative flow: Canva as final destination instead of Drive-approved assets.
No stale ownership: Geizian as merely parceiro instead of sócio.
No Ares overreach: Ares must not configure ChatPion/DigitalTrChat, quiz, SMS Funnel, SMS structure, AdOps blocks, or technical site setup without explicit scope.
SB/AV consistency: SB principal/preferred dashboard; AV exception for openzed/cliquet/subdomains.
Gestores/codes: Icaro g001, Geizian g002, Isliago g003, Joe g004, Kelly g005, Nicolas g006.
Finance: gestor commission belongs to Rodolfo's financial spreadsheet; salary/commission are not added together.
Permissions: executable access still comes from data/authorized-users.json.
Sites: conceptual sites.md does not imply pipeline readiness; data/sites.json wins for automation.
```

## Communication pattern that worked

Rodolfo prefers decision-level validation first. For each file, give:

1. concise summary of what changed;
2. 5-8 decisions he needs to validate;
3. opinion whether the file is coherent;
4. if he asks to see the file, show the actual file content, not only another summary.

## Pitfall

Do not rely on a regex-only audit as proof of semantic consistency; use it as a guardrail, then read/inspect the relevant snippets if the regex flags false positives or misses context. Report only real residual conflicts, not every intentionally negative statement such as “Ares não configura ChatPion.”
