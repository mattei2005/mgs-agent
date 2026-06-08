# Company OS Blueprint Session — 2026-06-05

## Context

Rodolfo shared a course/reference from Bruno, described as a respected agent architecture/structure practitioner. The key insight from Rodolfo: MGS may have started by creating agents before formally structuring the company, areas, routes, and sources those agents should read/write.

Operational interpretation: MGS currently has functioning agents and production assets, but needs a formal company operating layer before scaling additional agents.

## User concern

Rodolfo asked whether reorganizing the company structure would require replacing existing files. The answer should distinguish:

- Bad approach: rebuild everything and swap many files at once.
- Good approach: create a company OS layer above the current operational foundation, then migrate incrementally.

Recommended wording:

```text
Não precisa refazer tudo e trocar tudo.
O certo é criar uma camada nova de organização por cima,
migrar o que presta e só substituir o que estiver mal encaixado.
```

## Current structural inventory observed

Scope: `/root/mgs-agent`, excluding individual agent profile files and `profiles/` sync copies.

Approximate structural counts from the session:

```text
Area                         Qty    Meaning
--------------------------- ------ --------------------------------------------
context/                       7    Conceptual company knowledge
data/                         55    Operational data, states, inventories
docs/                         26    Documentation, pendencies, changelog, crons
scripts/                      59    Automations, monitors, runners, importers
skills/                      115    Structural content/publishing skills
patches/                      30    Local Hermes/MGS patches
backups/                      13    Crontab/config/old-file backups
experiments/                  30    Honcho/memory experiments and spikes
tools/                        13    Auxiliary tooling such as Canva automation
api/                           1    Internal REC generation API
```

Most important current files:

```text
Layer                    Main files
------------------------ -------------------------------------------------------
Company                  context/company.md
Sites                    context/sites.md, data/sites.json
Team/permissions         context/team.md, data/authorized-users.json
Processes                context/processes.md
Monetization             context/monetization.md
Acquisition              context/acquisition.md
Security                 context/security-policies.md
Crons/ops                docs/CRONS.md, scripts/monitor-*.sh
Pendency tracking        docs/PENDENCIAS.md, docs/PENDENCIAS-HISTORICO.md
REC/P1 content           skills/content-generate-rec/, scripts/mgs-rec-runner.py
WordPress publishing     skills/content-publish-wordpress/
Audit/state              data/infra-inventory.json, data/mgs-ops-control-plane-latest.json
```

## First blueprint deliverable

Created/proposed path:

```text
/root/mgs-agent/context/company-os.md
```

Status should initially be **proposal**, not automatically canonical.

Core sections used:

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

## Recommended areas and agents

```text
Area             Function
--------------- ---------------------------------------------------------------
Executive/Ops    Governance, priorities, authorizations, audit, coordination
Content          REC, P1, WordPress, editorial QA, publishing
Growth/Ads       Acquisition, campaigns, tracking, funnels, paid media
Tech/Infra       VPS, Hermes, bots, crons, patches, WordPress technical services
Data/BI          Metrics, reports, cost, performance, operational intelligence
Finance          Revenue, costs, ROI, monetization, economics
Security         Access, credentials, hardening, permissions, risk policy
```

```text
Agent   Primary area    Role
------- --------------- ------------------------------------------------------
Zeus    Executive/Ops   General Manager, governance, routing, audit, escalation
Atena   Content         Editorial production, REC/P1, WordPress, content QA
Ares    Growth/Ads      Campaigns, acquisition, tracking, ads, funnels
Future  TBD             Specialist agents created only after mission/scope exist
```

## Migration rule

Use staged gates:

```text
1. Blueprint read-only / additive
2. Classified inventory
3. New canonical context files
4. Agent reference updates
5. Cleanup/archival after explicit approval
```

Do not delete/move/rename live operational files in the blueprint stage.

## Next suggested deliverable after blueprint approval

Create:

```text
/root/mgs-agent/docs/mgs-structure-inventory.md
```

With columns:

```text
Path | Classe | Dono | Área | Status | Ação recomendada
```

Actions should be conservative: `manter`, `não tocar`, `mover`, `renomear`, `consolidar`, `arquivar`, `remover depois`, `revisar com Rodolfo`.
