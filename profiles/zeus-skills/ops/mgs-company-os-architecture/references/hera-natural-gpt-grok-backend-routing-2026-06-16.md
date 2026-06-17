# Hera natural GPT/Grok creative backend requests — 2026-06-16

Use this reference when aligning Hera Creative Ops or MGS Company OS around multiple creative generation backends.

## User-intended operating model

Rodolfo wants Hera to accept normal creative requests and backend preferences in natural language:

```text
“Hera, faz esse criativo com Grok.”
“Hera, faz com GPT.”
“Hera, faz nos dois e compara.”
“Hera, anima esse avatar com Grok.”
```

This is not a request to create a new Grok-specific agent. Hera remains Creative Operations owner. GPT/OpenAI-Codex and Grok/xAI are tools under Hera.

## Routing rule

```text
Request wording                         Hera routing
──────────────────────────────────────  ─────────────────────────────────────────
com GPT / ChatGPT / OpenAI              GPT/OpenAI-Codex image generation.
com Grok                                Grok/xAI explicit wrapper or xAI media tool.
os dois / comparar                      Generate both variants; compare quality/use case.
vídeo / avatar / image-to-video         Prefer Grok/xAI video/reference-image workflow.
no backend specified                    Pick best fit: GPT for static iteration; Grok for video/avatar.
```

## Governance boundaries

- Hera creates and organizes creative assets; Ares consumes approved assets for campaigns when relevant.
- Ares may use xAI/X search for trends, but enabling Grok media does not make Ares the owner of creative production.
- Atena remains Content Operations; do not turn Grok creative media into an editorial default unless Rodolfo explicitly approves.
- Zeus orchestrates, audits, monitors cost/errors and handles safe rollout.

## SOUL alignment pattern

When patching Hera SOUL, add a compact “Backends criativos — GPT e Grok” section rather than a long provider manual. Include:

- natural-language trigger examples;
- GPT path;
- Grok image/video/avatar path;
- “os dois” comparison path;
- metadata sanitization still required before Drive/handoff;
- no credential/token output.

Keep detailed OAuth/setup steps in `hermes-agent-operations`, not in Hera SOUL.
