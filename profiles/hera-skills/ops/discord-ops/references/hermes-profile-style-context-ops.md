# Hermes Profile Style + Context Access Ops

Use this reference when Rodolfo asks to make Zeus/Atena less verbose, adjust SOUL.md behavior, or create an OpenClaw-style “reindex” equivalent without changing Hermes memory providers.

## Executive style patch pattern

Do not paste course/persona text raw into SOUL.md. Adapt it to MGS operational tone:

- direct opening; no “Com certeza”, “Claro”, “Great question”
- no closing filler like “Fico à disposição”
- no repetition of the user’s request
- short executive prose by default
- bullets/tables only when parallel/comparative
- clear operational opinion; investigate instead of hedging
- no emoji in normal replies
- can disagree when it improves clarity, speed, safety, or quality
- preserve respect for Rodolfo as CEO and Zeus safety rules

Suggested section title:

```md
### Modo executivo curto — teste ativo
```

Keep the label “teste ativo” when the user wants an easy rollback trial.

## Safe SOUL.md edit sequence

1. Keep `agent.reasoning_effort` unchanged unless explicitly approved.
2. Read the relevant SOUL.md section.
3. Create timestamp backup:

```bash
cp /root/.hermes/profiles/{agent}/SOUL.md \
  /root/.hermes/profiles/{agent}/SOUL.md.bak-$(date +%Y%m%d-%H%M%S)
```

4. Patch only the target tone/style section.
5. Verify by re-reading the patched lines.
6. Run config validation when available:

```bash
hermes config check
```

7. If the change is structural/profile behavior, send `[REPORT-INFRA]`.

Rollback:

```bash
cp /root/.hermes/profiles/{agent}/SOUL.md.bak-YYYYMMDD-HHMMSS \
  /root/.hermes/profiles/{agent}/SOUL.md
```

## Hermes “indexing” equivalent without memory provider changes

Hermes built-in memory is file-backed (`memories/MEMORY.md`, `memories/USER.md`) and injected into context, not a vector index. If Rodolfo asks for “indexação” but does not want memory/provider changes, do a read-only manifest instead:

- enumerate canonical context files
- confirm readability
- record size, mtime, and short hash
- optionally add a short human summary and priority

Typical sources:

```text
/root/.hermes/profiles/{agent}/memories/MEMORY.md
/root/.hermes/profiles/{agent}/memories/USER.md
/root/.hermes/profiles/{agent}/SOUL.md
/root/.hermes/profiles/{agent}/config.yaml
/root/mgs-agent/AGENT.md
/root/mgs-agent/CLAUDE.md
/root/mgs-agent/context/*.md
```

This validates access and freshness without changing retrieval, embeddings, or external memory providers.

## Warm-up prompt bank after model/profile change

Use these as questions for a short post-change calibration:

1. Qual é seu papel na MGS em uma frase?
2. Quais são suas fontes canônicas antes de responder sobre operação?
3. Quais decisões você nunca pode executar sem confirmação do Rodolfo?
4. Como você deve responder quando não tiver dado suficiente?
5. Qual é o fluxo correto quando Atena pede autorização para usuário externo?
6. O que você deve fazer antes de declarar uma tarefa concluída?
7. Qual é o padrão de resposta esperado pelo Rodolfo: curto, detalhado ou consultivo?
8. Quais são os principais riscos operacionais atuais da MGS que você deve monitorar?
9. Como você diferencia fato verificado de inferência?
10. Me dê um status executivo da operação MGS em até 5 bullets, consultando fontes reais.

## Pitfalls

- Do not convert style preference into `reasoning_effort` change unless user explicitly wants that.
- Do not activate semantic memory providers as a substitute for verbosity control.
- Do not claim Hermes has an OpenClaw-style `memory index --force` equivalent for built-in memory.
- Do not save temporary hashes/backups as durable memory; they are session artifacts.
