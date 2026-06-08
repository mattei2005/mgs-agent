# REC+P1 post-restructure validation, reporting and latency lessons — 2026-06-08

## Context

After the REC/P1 contract/runners were restructured, Rodolfo asked Atena to publish:

```text
Site: eggbev
Vertical: gb-cc-en
Card: Tesco Bank Balance Transfer Credit Card
Official URL: https://www.tescobank.com/credit-cards/balance-transfer-credit-card/
Status: publish/publicado
```

Atena produced REC `62425` and P1 `62429`, but the first production run exposed reporting-format and latency lessons that should govern future REC+P1 operations.

## Final report format preferred by Rodolfo

Use the compact report format. Do **not** show separate lines with the text of Subtitle or Excerpt by default.

Preferred validation line per article:

```text
• Validação: <palavras> palavras / subtitle <chars> chars / excerpt <chars> chars / público HTTP <codigo>
```

Then continue with:

```text
• Title: <titulo> — <chars> chars
• Focus: <palavra chave>
• Meta Description: <texto> — <chars> chars
• Tags: <tags>
• Imagem Card: <url>
• Imagem Featured: <url>
• Fonte oficial: <url>
```

Only show explicit `Subtitle: <texto>` / `Excerpt: <texto>` lines if Rodolfo/Raquel asks for an expanded QA/editorial version.

## Renderer discipline

For normal REC+P1, use the deterministic renderer when runner JSON exists:

```bash
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

Do not assemble the final REC+P1 report manually unless the renderer cannot be used and the reason is stated. Manual reports easily omit required fields, timings or costs.

## Latency lesson

The Tesco run took about `21m44s` perceived wall-clock time (`1304.5s`, 78 model API calls, 77 tool turns). This is not an acceptable steady-state benchmark.

Primary causes observed:

```text
- live patching during production instead of blocking/reporting a structural gate
- multiple failed orchestrator runs
- repeated image upload/delete cycles
- REC and P1 QA/repair loops
- very large context growth (~115k tokens)
- final validation/reporting done manually instead of one renderer call
```

Expected target after fixes:

```text
Good REC+P1 publish:       3–5 min
Acceptable with heavy img: <=7 min
Inacceptable:              20+ min
```

Future REC+P1 production should not repeatedly patch/retry inside the user-facing run. If a structural gate fails, block/report or run a focused repair, then re-run cleanly.

## Operational checklist for future REC+P1 publish runs

1. Run orchestrator cleanly; avoid ad-hoc manual substeps unless diagnosing a failed run.
2. Limit image retries; reuse validated card image within the same run.
3. Keep official-source and card-image gates strict, but avoid false blockers already documented in `tesco-balance-transfer-runner-fixes-2026-06-08.md`.
4. Ensure WordPress tags and LazyBlock tags are derived from confirmed benefits/facts, not generic commercial fallbacks.
5. Render final summary through `render-article-summary.py`.
6. Report both runner timing and perceived operation timing when retries/repairs happened.
7. If total time exceeds 7 minutes, include a latency note with the root cause.