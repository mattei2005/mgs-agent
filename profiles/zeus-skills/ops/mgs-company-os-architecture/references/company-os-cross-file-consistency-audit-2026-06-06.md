# Company OS cross-file consistency audit — 2026-06-06

Use this note when reviewing or restructuring MGS Company OS context files after Rodolfo provides new operational corrections.

## Durable lesson

A correction made while reviewing one document can invalidate earlier documents. Do not treat a previously approved file as permanently safe when Rodolfo adds a new concept, ownership rule, route, permission, or naming correction.

## Required cascade pattern

When a new correction appears:

1. Apply it to the current file under review.
2. Search already-reviewed Company OS docs for stale terms, contradictions, and outdated ownership/routes.
3. Patch conflicts before moving to the next file.
4. Run a semantic consistency checklist, not only `git diff --check`.
5. Report the cascade explicitly in a short table: file, issue found, action taken.

## Canonical cascade targets

Check at minimum:

- `context/company.md`
- `context/company-os.md`
- `context/company-current-operating-model.md`
- `context/areas.md`
- `context/agent-map.md`
- `context/routes.md`
- `context/sources-of-truth.md`
- `context/permissions-matrix.md`
- `docs/mgs-os-restructure-plan.md`
- `docs/mgs-structure-inventory.md`

## Example consistency checks from this session

- Ares must be **Ares**, never `Aris`.
- Do not call Ares `Ares futuro`; use status/context such as `em configuração` or `implantação progressiva`.
- agente legado is the creative agent; Kelly is the human gestor/creative lead (`g005`).
- Ares handles campaigns/media buying, but does **not** configure ChatPion/DigitalTrChat, quiz, SMS Funnel, or SMS structure.
- agente legado and Ares both need read/write access to the approved-creatives Google Drive.
- Smart Bidding and ActiveView are Google partner companies with AdX/Ad Manager networks; Smart Bidding is the preferred/main dashboard, while ActiveView remains active for `openzed`, `cliquet`, and subdomains.
- Geizian is Rodolfo's sócio and also operating gestor `g002`.
- Ially is Office / Follow-up and handles cobranças/follow-up of gestores when tasks are delayed or not done.
- Rodolfo commands the AI-agent operation as a whole, not only Ares.
- Gestor commission belongs in Finance/BI context and must align with planilha financeira rules.

## Reporting pattern

Use concise executive output:

```text
Checagem cruzada
----------------
Arquivos verificados: N
Regras checadas:     N
Falhas finais:       0
Whitespace:          OK

Arquivo                    Correção
-------------------------  --------------------------------
context/company-os.md       Removed stale Creative Agent wording.
context/agent-map.md        Added explicit Ares boundary.
```

Avoid making Rodolfo review raw file contents when he is asking for assurance; report the actual consistency result and any conflicts fixed.