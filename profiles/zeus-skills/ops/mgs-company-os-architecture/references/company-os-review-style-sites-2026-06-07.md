# Company OS Review Lessons — 2026-06-06/07

Session-specific lessons from the MGS Company OS review with Rodolfo.

## Review presentation preference

Rodolfo does **not** want whole markdown files pasted into chat for review. Preferred patterns:

1. For normal review: SOUL-style sections:
   - `O que faz sentido`
   - `O que está demais / arriscado`
   - `O que falta`
   - `Pontos para Rodolfo classificar/corrigir`
2. When he asks to see the file whole: send it as a native attachment (`MEDIA:/tmp/<name>.md`) so Discord shows a clickable preview/card. Do not inline the full file unless explicitly requested.

## Workflow correction

Before calling a file ready for review, run a cascade check against files already reviewed. Rodolfo explicitly called out that corrections in one file can reveal redundancy/conflict in previous files. The check should include not only wrong facts, but also redundant structure that belongs elsewhere.

Example from this session: `context/sites.md` had a full `## Regra de conflito` section. Rodolfo questioned whether it belonged there. Correct resolution: remove it from `sites.md` because detailed source-priority rules already live in `context/sources-of-truth.md`; keep only a short note that `sites.md` is conceptual and `data/sites.json` wins for automation.

## Updated conceptual sites list

Rodolfo provided an updated conceptual portfolio list. In `context/sites.md`, it was applied as 45 unique domains / 89 domain-vertical entries, grouped by CC, GAME, CAR, JOB.

Important additions/updates:

```text
gamingadx.com                 US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamezonead.com                US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamehubad.com                 US-GAME-EN, BR-GAME-BR, MX-GAME-ES
creditoparaveiculo.com        BR-CAR-BR, PT-CAR-PT
financiamentoautoadx.com      BR-CAR-BR, PT-CAR-PT
financiarveiculo.com          BR-CAR-BR, PT-CAR-PT
autocreditadx.com             US-CAR-EN, MX-CAR-ES
carcreditad.com               US-CAR-EN, MX-CAR-ES
autolendpro.com               US-CAR-EN, MX-CAR-ES
wavesbee.com                  US-CC-EN
finanzas.wavesbee.com         US-CC-ES
conectageral.com              US-CC-EN
finanzas.conectageral.com     US-CC-ES
portalrelevante.com           US-CC-EN
finanzas.portalrelevante.com  US-CC-ES
```

Do not treat this conceptual list as proof that automation is configured. `data/sites.json` remains the technical source for automated pipelines.
