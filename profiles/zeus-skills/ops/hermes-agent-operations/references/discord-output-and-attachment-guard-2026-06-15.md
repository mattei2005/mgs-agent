# Discord output and attachment guard — MGS Zeus

## Trigger

Rodolfo corrected Zeus after repeated Discord rendering problems and unsolicited file previews/attachments during an MGS OS organogram/map review.

## Durable rules

- Do not send files/attachments to Rodolfo unless he explicitly asks for an attachment/file.
- If Rodolfo says “por aqui”, “no chat”, or simply asks to see/explain/review, respond inline.
- Avoid language-tagged code fences in Discord final replies (` ```text`, ` ```bash`, ` ```json`). Some clients/gateway previews can leak the language label as a standalone `text` line and make the response look broken.
- Avoid many small code blocks; prefer bullets and short sections.
- Avoid raw Markdown pipe tables in Discord responses; use bullets or aligned plain text only if necessary.

## Mechanism implemented

A local guard was created:

- `/root/mgs-agent/scripts/discord-response-lint.py`

It checks drafts for:

- language-tagged code fences;
- standalone `text` lines;
- too many code fences;
- raw Markdown pipe tables;
- `MEDIA:/...` attachment directives.

Use it for long operational drafts when formatting risk is high:

- `python3 /root/mgs-agent/scripts/discord-response-lint.py --check <draft>`
- `python3 /root/mgs-agent/scripts/discord-response-lint.py --fix <draft>` for simple fence/label cleanup.

## SOUL impact

Zeus SOUL should contain a rule equivalent to:

- no unsolicited attachments;
- if Rodolfo asks to see it here, answer inline;
- only use attachments after explicit request;
- use lint/mental lint for long Discord operational reports.

## Pitfall

Do not solve long-document readability by attaching files automatically. First provide a concise inline executive view; only offer an attachment if it would help, and wait for explicit approval/request before sending it.
