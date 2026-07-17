# MGS OS map file + HOT pointer pattern

## Trigger

During an organogram/MGS OS structure review, Rodolfo clarified that “mapa” means a literal operational map for Zeus: a small navigation layer that helps locate the right file/folder/agent quickly, reducing unnecessary broad `search_files` calls.

## Decision

Do not embed a large map directly into Zeus SOUL. Instead:

1. Create/maintain a full map file:
   - `/root/mgs-agent/context/mgs-os-map.md`
2. Add only a compact HOT pointer in Zeus SOUL:
   - consult `context/mgs-os-map.md` before broad search for structure-related questions;
   - the map directs investigation but does not replace runtime validation.

## What the map should contain

- quick source list: company OS, areas, agents, routes, permissions, sites, crons, audit log;
- map by area: Executive, Office, Content, Growth, Creative, Revenue/AdOps, Finance/BI, Tech/Infra, Security;
- map by agent: Zeus, Atena, Ares, agente legado with live and versioned paths;
- map by folder: `context/`, `data/`, `docs/`, `scripts/`, `profiles/`, `/root/.hermes/profiles/`, `logs/`, `patches/`, `backups/`, `tools/`, `experiments/`;
- question → first source, e.g.:
  - “Quem faz o quê?” → `context/agent-map.md`, `context/areas.md`, `context/routes.md`;
  - “Permissão real?” → `data/authorized-users.json`;
  - “Cron ativo?” → `docs/CRONS.md` + crontab real;
  - “Atena fez X?” → Atena logs + tracker + WP/API when needed;
  - “Honcho está como quê?” → `scripts/mgs-memory-copilot`, Honcho spike scripts/README, SOULs.
- risk map: low/medium/high/critical paths.

## SOUL pointer pattern

Keep the SOUL pointer short. Example wording:

“Regra de navegação HOT: antes de usar busca ampla para perguntas correlacionadas à estrutura MGS, consulte `/root/mgs-agent/context/mgs-os-map.md` para escolher o arquivo/fonte certo. O mapa não substitui validação em runtime; ele direciona a investigação.”

## Pitfalls

- Do not treat `mgs-os-map.md` as a source of truth for live state; it is a navigation index.
- Do not let the map drift from `sources-of-truth.md`, `agent-map.md`, `areas.md`, `routes.md`, and `permissions-matrix.md`.
- Do not solve navigation by adding a huge map to SOUL; HOT should stay compact.
- When Rodolfo asks to review the map inline, do not attach the file unless explicitly requested.
