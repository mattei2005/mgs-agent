# Deterministic final article summary renderer — 2026-05-26

## Trigger

Use after successful REC, P1, or REC+P1 runner completion when replying to Rodolfo in Discord.

## User correction

Rodolfo corrected that final article summaries must match his supplied template exactly. This is not just field coverage; the output must preserve the same emojis, labels, order, bullets, spacing, and line breaks. Placeholder text is replaced with real runner values only.

## Operational pattern

Do not hand-rewrite the final summary from memory. Save runner JSON and render it deterministically:

```bash
# REC
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec <rec-json>

# P1
python3 /root/mgs-agent/scripts/render-article-summary.py --type p1 <p1-json>

# REC+P1
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

The legacy P1 wrapper remains valid but should be treated as compatibility only:

```bash
python3 /root/mgs-agent/scripts/render-p1-summary.py <p1-json>
python3 /root/mgs-agent/skills/content-generate-rec/scripts/render-p1-summary.py <p1-json>
```

## Hard gates

- Use the renderer output as the Discord reply.
- Do not add intro text, mentions, tables, extra audit sections, Markdown restyling, or alternate layouts unless Rodolfo explicitly updates the template for that request.
- If the runner failed or any hard validation gate failed, do not use the success template as-is; report the objective blocker instead.
- For REC+P1, render both runner outputs together with `--type rec-p1`; do not send two separate final summaries.

## Verification pattern

Before treating the formatter as fixed, run syntax checks plus a small sample for all three modes:

```bash
python3 -m py_compile \
  /root/mgs-agent/scripts/render-article-summary.py \
  /root/mgs-agent/scripts/render-p1-summary.py \
  /root/mgs-agent/skills/content-generate-rec/scripts/render-p1-summary.py

python3 /root/mgs-agent/scripts/render-article-summary.py --type rec /tmp/rec.json
python3 /root/mgs-agent/scripts/render-article-summary.py --type p1 /tmp/p1.json
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 /tmp/rec.json /tmp/p1.json
```

## Why this matters

Manual formatting was the failure point: even with the right facts available, Atena varied the final report. The deterministic renderer is the safer, faster path: runner JSON → renderer → paste exact output into Discord.
