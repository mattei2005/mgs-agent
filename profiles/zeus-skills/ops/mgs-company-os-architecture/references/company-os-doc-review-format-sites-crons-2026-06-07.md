# Company OS doc review — format, cascade, sites and crons notes

Session lessons from Rodolfo's review of MGS Company OS docs on 2026-06-07.

## Review presentation preference

Rodolfo rejected two review patterns:

- pasting the whole Markdown file inline in Discord;
- only giving a high-level summary when he wants to read the whole artifact.

Preferred pattern:

1. Zeus reads the file and gives a SOUL-style review:
   - `O que faz sentido`
   - `O que está demais / arriscado`
   - `O que falta`
   - `Pontos para Rodolfo classificar/corrigir`
2. If Rodolfo asks to see/read the full file, send it as a native attachment (`MEDIA:/tmp/<file>-review.md`) so he can click and open it.
3. Do not paste long files inline unless he explicitly requests inline text.

## Cascade discipline

Rodolfo reiterated that every correction in the current file can invalidate previously reviewed docs. Do the cascade check before presenting a file as ready, not after he catches the issue.

Checks that mattered in this session:

- stale agent names: `Aris`, `Ares futuro`, `Kelly agent`, `agente Kelly`, `Creative Agent`;
- Ares overreach into ChatPion/DigitalTrChat, quiz, SMS Funnel, AdOps blocks, or site technical setup;
- Geizian as `sócio`, not generic partner;
- agente legado as creative agent; Kelly as human gestor/creative lead (`g005`);
- `data/sites.json` vs `context/sites.md` automation boundary;
- Smart Bidding main dashboard vs ActiveView exceptions.

## Domain docs should not duplicate global governance

A `## Regra de conflito` section inside `context/sites.md` was judged unnecessary because `context/sources-of-truth.md` already owns precedence/conflict rules. For domain files, prefer a short pointer:

```text
This file is conceptual. For automation, credentials, templates and technical status, `data/sites.json` wins.
```

Keep full conflict matrices in `sources-of-truth.md`.

## `context/sites.md` update pattern

When Rodolfo supplies a fresh site list:

- group by vertical class (`CC`, `GAME`, `CAR`, `JOB`);
- preserve domains with multiple verticals as one row where possible;
- count both unique domains and domain/vertical rows;
- validate that added domains/verticals are represented;
- send the updated file as an attachment for review.

Validated list in this session ended at 45 unique domains and 90 domain/vertical entries after adding `fincgriffin.com US-CAR-EN` under CAR as well as the existing CC rows.

## `docs/CRONS.md` review pattern

Treat `docs/CRONS.md` as generated inventory documentation. Safe review path:

1. Regenerate via `/root/mgs-agent/scripts/cron-control-plane.py --write-doc` only when the task is document review; do not edit crontab/runtime.
2. Run `git diff --check` and trim generated trailing whitespace if needed.
3. Attach the generated doc.
4. Review as inventory, not as desired-state architecture.
5. Call out unclassified risks and live anomalies found from logs, but do not change cron entries without explicit approval.

In this session, the doc had 19 active root crons; `hermes-news-explainer.py` and `monitor-webshare-status.sh` were unclassified, and `monitor-auto-push.sh` showed consecutive failures in the log. Those are review findings, not automatic permission to change runtime.
