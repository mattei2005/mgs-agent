# REC agent prompt over-reading audit

Use this reference when Rodolfo/Zeus asks why Atena is taking too long before or around REC production, or asks to inspect prompt/config files for loops.

## Durable lesson

The observed problem is usually not a single infinite loop. It is an over-reading pattern caused by several prompt/doc layers that all encourage loading large files before acting. In a REC direct-publish path, this inflates context, cache reads, and tool calls even when the deterministic runner could do the job in one command.

## Symptoms to check

- REC request is complete, but Atena loads `content-generate-rec` fully, reads `AGENT.md`, opens runner/template files, or starts browser research before calling `mgs-rec-runner.py`.
- Session metrics show high tool output/context compared with runner time.
- `skill_view content-generate-rec` contributes ~60 KB by itself.
- `AGENT.md` contributes ~17 KB if read in full.
- Tool output dominates the session, while runner `duration_sec` is much lower than Discord elapsed time.

## Known prompt/document causes

1. Hermes global skills prompt may say to load a skill if it is even partially relevant and to err on the side of loading. That is too aggressive for fast-path REC work.
2. Atena SOUL historically contained phrases like “Leia AGENT.md agora”, which can induce repeated full reads of the master file.
3. `AGENT.md` may still include legacy REC flow rules such as human pauses/manual steps that conflict with the direct runner path.
4. The main REC skill is large. Loading the full skill is useful for audits/debugging, but expensive for normal REC publishing.
5. A truncated SOUL/system prompt can suggest using tools to read the full file, which encourages more reading unless scoped.

## Correct behavior for future sessions

- For a complete REC request (site + card + status + official URL/source), do not perform prompt/file audits first. Call `mgs-rec-runner.py` once and summarize its JSON.
- Treat long skills, `AGENT.md`, templates, and runner source as references for debugging, not as required preflight reads.
- If a file must be inspected, read the smallest relevant section, not the entire file.
- Do not reread a file already inspected in the same task unless the file changed or the user asks for that specific section again.
- Do not broaden a normal publish request into an audit. If the user asks for speed/prompt audit, keep the scope to prompt/read-loop causes and summarize with metrics.

## Recommended patches when auditing configuration

- In Atena SOUL: replace “Leia AGENT.md agora” with “AGENT.md is canonical; consult it only when a decision depends on authorization, critical subset, reporting, or a rule not already present in prompt context.”
- In REC guidance: explicitly state that complete REC direct-publish requests bypass full skill/template/manual workflow reads.
- In AGENT.md: mark old REC human-pause/manual steps as legacy unless the runner fails or the user requests manual workflow.
- In Hermes global prompt, if editable: change “partially relevant / err on loading” to “clearly necessary / load the narrowest relevant skill or reference.”

## Reporting pattern

When reporting to Rodolfo, distinguish:

```text
Finding                      | Meaning
-----------------------------|------------------------------------------
Runner duration_sec          | Actual deterministic pipeline time
Discord elapsed time         | Includes agent reading, QA, patches, talk
Tool output/context volume   | Main indicator of over-reading
Legacy/manual instructions   | Risk factor for slow non-runner behavior
```

Avoid exposing credentials or raw tokens. Report token/tool metrics only as operational cost/context indicators.